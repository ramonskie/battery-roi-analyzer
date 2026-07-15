"""Async wrapper around Home Assistant's Recorder Statistics API.

Never touches the Recorder database/SQLite directly. All access goes through
``get_instance(hass).async_add_executor_job(...)`` so blocking SQLAlchemy
session work never runs on the event loop, per HA integration standards.

Provides a best-available-resolution fallback chain (5minute -> hour -> day)
for a set of energy sensors (import/export/production/consumption) over a
date range, returned as pandas DataFrames for downstream resampling in
``simulator.py``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Final, Literal

import pandas as pd
from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.statistics import (
    async_list_statistic_ids,
    get_last_statistics,
    statistics_during_period,
)
from homeassistant.core import HomeAssistant

# Resolutions tried in order, best (finest) first, until one yields data.
_RESOLUTION_FALLBACK_CHAIN: Final[tuple[Literal["5minute", "hour", "day"], ...]] = (
    "5minute",
    "hour",
    "day",
)

_STAT_TYPES: Final[set[str]] = {"state", "sum", "mean", "min", "max"}

_COLUMNS: Final[tuple[str, ...]] = (
    "start",
    "end",
    "state",
    "sum",
    "mean",
    "min",
    "max",
)


@dataclass(slots=True, frozen=True)
class StatisticsResult:
    """Result of a statistics fetch for a single entity_id.

    Attributes:
        entity_id: The statistic/entity id the data belongs to.
        resolution: The granularity that actually yielded data (or the
            coarsest one tried, if none yielded data).
        dataframe: Time-indexed DataFrame (UTC, column ``start`` as index)
            with columns from ``_COLUMNS`` (minus ``start``). Empty
            DataFrame (with correct columns) if no statistics exist yet.
    """

    entity_id: str
    resolution: Literal["5minute", "hour", "day"]
    dataframe: pd.DataFrame


def _empty_dataframe() -> pd.DataFrame:
    """Build an empty, correctly-typed DataFrame for the "no data" case."""
    frame = pd.DataFrame(columns=[c for c in _COLUMNS if c != "start"])
    frame.index = pd.DatetimeIndex([], tz=timezone.utc, name="start")
    return frame


def _rows_to_dataframe(rows: list[dict]) -> pd.DataFrame:
    """Convert raw StatisticsRow dicts (float unix seconds) into a DataFrame.

    Args:
        rows: Raw rows as returned by ``statistics_during_period`` for one
            statistic_id (values are float unix-second timestamps).

    Returns:
        DataFrame indexed by UTC ``start`` timestamp, sorted ascending.
    """
    if not rows:
        return _empty_dataframe()

    frame = pd.DataFrame(rows)
    for column in ("start", "end"):
        if column in frame.columns:
            frame[column] = pd.to_datetime(frame[column], unit="s", utc=True)
    frame = frame.set_index("start").sort_index()
    # Only keep columns we know about; missing ones become NaN so downstream
    # code can rely on a stable schema regardless of requested `types`.
    for column in _COLUMNS:
        if column not in {"start", *frame.columns}:
            frame[column] = pd.NA
    return frame


async def async_get_statistic_ids(
    hass: HomeAssistant, entity_ids: set[str]
) -> set[str]:
    """Return the subset of `entity_ids` that currently have statistics.

    Uses the async-cached `async_list_statistic_ids` wrapper (checks an
    in-memory metadata cache before falling back to an executor job), as
    recommended over hand-rolling `list_statistic_ids` in an executor job.

    Args:
        hass: The Home Assistant instance.
        entity_ids: Candidate entity ids to check.

    Returns:
        Subset of `entity_ids` for which the recorder has (or will soon
        compile) statistics. Entities with no `state_class` or not yet
        compiled are excluded.
    """
    known = await async_list_statistic_ids(hass, statistic_ids=entity_ids)
    return {item["statistic_id"] for item in known}


async def _async_fetch_period(
    hass: HomeAssistant,
    entity_id: str,
    start_time: datetime,
    end_time: datetime | None,
    period: Literal["5minute", "hour", "day"],
    target_unit: str | None = "kWh",
) -> list[dict]:
    """Fetch one resolution of statistics for a single entity via executor.

    Always requests conversion to ``target_unit`` (kWh by default) so
    sensors using MWh, Wh, or any other energy unit are normalised to
    the single unit the battery simulator expects.

    Args:
        hass: The Home Assistant instance.
        entity_id: Statistic/entity id to fetch (also the statistic_id for
            natively-tracked HA sensors).
        start_time: UTC inclusive lower bound.
        end_time: UTC exclusive upper bound, or None for "up to now".
        period: Requested granularity.
        target_unit: Requested output unit. The recorder returns
            statistics converted to this unit. ``None`` means
            no conversion (raw stored unit).

    Returns:
        Raw list of StatisticsRow dicts for `entity_id` (empty list if none).
    """
    units: dict[str, str] | None = {entity_id: target_unit} if target_unit else None
    result = await get_instance(hass).async_add_executor_job(
        statistics_during_period,
        hass,
        start_time,
        end_time,
        {entity_id},
        period,
        units,
        _STAT_TYPES,
    )
    return result.get(entity_id, [])


async def async_get_statistics(
    hass: HomeAssistant,
    entity_id: str,
    start_time: datetime,
    end_time: datetime | None = None,
) -> StatisticsResult:
    """Fetch statistics for one entity at the best available resolution.

    Tries the fallback chain (5minute -> hour -> day) in order and returns
    the first resolution that yields at least one row. If none of them do
    (e.g. entity has no statistics compiled yet), returns an empty
    DataFrame tagged with the coarsest resolution ("day").

    Args:
        hass: The Home Assistant instance.
        entity_id: Statistic/entity id to fetch.
        start_time: UTC inclusive lower bound.
        end_time: UTC exclusive upper bound, or None for "up to now".

    Returns:
        A `StatisticsResult` with the resolved resolution and DataFrame.
    """
    last_period: Literal["5minute", "hour", "day"] = _RESOLUTION_FALLBACK_CHAIN[-1]
    for period in _RESOLUTION_FALLBACK_CHAIN:
        last_period = period
        rows = await _async_fetch_period(hass, entity_id, start_time, end_time, period)
        if rows:
            return StatisticsResult(
                entity_id=entity_id,
                resolution=period,
                dataframe=_rows_to_dataframe(rows),
            )

    return StatisticsResult(
        entity_id=entity_id,
        resolution=last_period,
        dataframe=_empty_dataframe(),
    )


async def async_get_statistics_for_entities(
    hass: HomeAssistant,
    entity_ids: set[str],
    start_time: datetime,
    end_time: datetime | None = None,
) -> dict[str, StatisticsResult]:
    """Fetch statistics for multiple entities (e.g. import/export/production/consumption).

    Each entity is resolved independently against the fallback chain, since
    different sensors may have different amounts of history compiled.

    Args:
        hass: The Home Assistant instance.
        entity_ids: Statistic/entity ids to fetch (import, export,
            production, consumption sensors, etc).
        start_time: UTC inclusive lower bound.
        end_time: UTC exclusive upper bound, or None for "up to now".

    Returns:
        Mapping of entity_id -> `StatisticsResult`. Entities with no
        statistics at all still get an entry with an empty DataFrame, so
        callers can distinguish "no sensor configured" (key absent) from
        "sensor configured but no data yet" (empty DataFrame).
    """
    results: dict[str, StatisticsResult] = {}
    for entity_id in entity_ids:
        results[entity_id] = await async_get_statistics(
            hass, entity_id, start_time, end_time
        )
    return results


async def async_get_last_statistic(
    hass: HomeAssistant,
    entity_id: str,
    convert_units: bool = True,
) -> dict | None:
    """Return the most recent hourly statistic row for an entity, if any.

    Useful for coordinator "has new data since last run?" checks without
    pulling a full period. Wraps `get_last_statistics`, which has no async
    convenience wrapper in HA core, via the standard executor-job pattern.

    Args:
        hass: The Home Assistant instance.
        entity_id: Statistic/entity id to look up.
        convert_units: Whether to convert to the entity's current live
            display unit (requires the entity to still exist).

    Returns:
        The most recent `StatisticsRow` as a dict, or `None` if the entity
        has no statistics yet.
    """
    result = await get_instance(hass).async_add_executor_job(
        get_last_statistics,
        hass,
        1,
        entity_id,
        convert_units,
        _STAT_TYPES,
    )
    rows = result.get(entity_id, [])
    return rows[0] if rows else None
