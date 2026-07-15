"""Async wrapper around Home Assistant's Recorder Statistics API.

Never touches the Recorder database/SQLite directly. All access goes through
``get_instance(hass).async_add_executor_job(...)`` so blocking SQLAlchemy
session work never runs on the event loop, per HA integration standards.

Provides a best-available-resolution fallback chain (5minute -> hour -> day)
for a set of energy sensors (import/export/production/consumption) over a
date range, returned as pandas DataFrames for downstream resampling in
``simulator.py``.

Unit handling
-------------
HA stores statistics in each sensor's native unit (e.g. kWh, MWh, Wh).
The ``statistics_during_period`` API has a ``units`` parameter that *may*
convert on fetch, but relying on it is brittle across HA versions. This
module therefore performs **explicit post-fetch unit conversion** to kWh
so that downstream code (coordinator, simulator) always works in kWh
regardless of the sensor's native unit.
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
# Resolution preference: ``day`` first because:
#   1. Daily data is average-based (already a daily mean) — ideal for ROI.
#   2. HA retains daily statistics the longest (months–years).
#   3. The battery simulator resamples anyway; daily is sufficient.
#   4. 365 daily points vs 8760 hourly = 24× less data, faster.
# Falls back to ``hour`` then ``5minute`` for recently-added sensors.
_RESOLUTION_FALLBACK_CHAIN: Final[tuple[Literal["day", "hour", "5minute"], ...]] = (
    "day",
    "hour",
    "5minute",
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

# Maps known energy units to their multiplier to get to kWh.
_ENERGY_UNIT_TO_KWH: Final[dict[str, float]] = {
    "kWh": 1.0,
    "MWh": 1000.0,
    "Wh": 0.001,
}


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
        unit_of_measurement: The sensor's native unit as stored in the
            recorder metadata, or ``None`` if unknown. Used by the
            coordinator to normalise to kWh.
    """

    entity_id: str
    resolution: Literal["5minute", "hour", "day"]
    dataframe: pd.DataFrame
    unit_of_measurement: str | None = None


def _empty_dataframe() -> pd.DataFrame:
    """Build an empty, correctly-typed DataFrame for the "no data" case."""
    frame = pd.DataFrame(columns=[c for c in _COLUMNS if c != "start"])
    frame.index = pd.DatetimeIndex([], tz=timezone.utc, name="start")
    return frame


def _convert_sum_to_kwh(
    dataframe: pd.DataFrame,
    source_unit: str | None,
) -> pd.DataFrame:
    """Convert the ``sum`` column in-place to kWh if *source_unit* differs.

    Handles common energy units (MWh, Wh, kWh). Pass ``None`` to skip
    conversion (unit unknown → assume already kWh).

    Returns the (possibly mutated) DataFrame for chaining; if the unit is
    ``None`` or already ``kWh`` this is a no-op.
    """
    if source_unit is None:
        return dataframe
    factor = _ENERGY_UNIT_TO_KWH.get(source_unit)
    if factor is None or factor == 1.0:
        return dataframe
    if "sum" not in dataframe.columns:
        return dataframe
    dataframe = dataframe.copy()
    dataframe["sum"] = dataframe["sum"].astype(float) * factor
    return dataframe


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
) -> list[dict]:
    """Fetch one resolution of statistics for a single entity via executor.

    Data is returned in the **sensor's native stored unit** (kWh, MWh,
    Wh, …). Callers **must** apply ``_convert_sum_to_kwh`` afterwards
    to normalise to kWh — this is handled automatically by
    ``_async_fetch_with_unit``.

    We deliberately do **not** pass a ``units`` conversion dict to
    ``statistics_during_period`` because:
      * the parameter may be silently ignored on older HA versions;
      * doing the conversion ourselves in ``_convert_sum_to_kwh`` is
        simpler and works on every HA version;
      * it avoids double-conversion if both the API and we were to
        attempt the conversion.

    Args:
        hass: The Home Assistant instance.
        entity_id: Statistic/entity id to fetch (also the statistic_id for
            natively-tracked HA sensors).
        start_time: UTC inclusive lower bound.
        end_time: UTC exclusive upper bound, or None for "up to now".
        period: Requested granularity.

    Returns:
        Raw list of StatisticsRow dicts for `entity_id` (empty list if none).
    """
    result = await get_instance(hass).async_add_executor_job(
        statistics_during_period,
        hass,
        start_time,
        end_time,
        {entity_id},
        period,
        None,  # units  -- we do our own conversion in _convert_sum_to_kwh
        _STAT_TYPES,
    )
    return result.get(entity_id, [])


async def _async_get_unit_of_measurement(
    hass: HomeAssistant,
    entity_id: str,
) -> str | None:
    """Return the unit_of_measurement stored in the statistics metadata.

    Uses the cached ``async_list_statistic_ids`` wrapper. Returns ``None``
    when the entity has no statistics metadata yet (e.g. a newly added
    sensor that hasn't been compiled).
    """
    known = await async_list_statistic_ids(hass, statistic_ids={entity_id})
    for entry in known:
        if entry.get("statistic_id") == entity_id:
            return entry.get("unit_of_measurement") or entry.get("statistics_unit_of_measurement")
    return None


async def _async_fetch_with_unit(
    hass: HomeAssistant,
    entity_id: str,
    start_time: datetime,
    end_time: datetime | None,
) -> StatisticsResult:
    """Fetch statistics at best resolution AND resolve the unit_of_measurement.

    1. Asks the HA API for metadata to learn the sensor's native unit.
    2. Fetches data via the resolution fallback chain.
    3. Explicitly converts the ``sum`` column to kWh (if the native unit
       is MWh, Wh, etc.), so downstream code always works in kWh.

    This explicit conversion is more reliable than relying on the
    ``statistics_during_period *units*`` parameter, which may be silently
    ignored on older HA versions or fail for certain unit pairs.
    """
    # Resolve native unit FIRST (metadata fetch is async-cached so it's fast).
    unit = await _async_get_unit_of_measurement(hass, entity_id)

    last_period: Literal["5minute", "hour", "day"] = _RESOLUTION_FALLBACK_CHAIN[-1]
    for period in _RESOLUTION_FALLBACK_CHAIN:
        last_period = period
        rows = await _async_fetch_period(hass, entity_id, start_time, end_time, period)
        if rows:
            dataframe = _rows_to_dataframe(rows)
            dataframe = _convert_sum_to_kwh(dataframe, unit)
            return StatisticsResult(
                entity_id=entity_id,
                resolution=period,
                dataframe=dataframe,
                unit_of_measurement=unit,
            )

    return StatisticsResult(
        entity_id=entity_id,
        resolution=last_period,
        dataframe=_empty_dataframe(),
        unit_of_measurement=unit,
    )


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

    The returned ``StatisticsResult.dataframe["sum"]`` is always in **kWh**
    regardless of the sensor's native unit (MWh, Wh, etc.).

    Args:
        hass: The Home Assistant instance.
        entity_id: Statistic/entity id to fetch.
        start_time: UTC inclusive lower bound.
        end_time: UTC exclusive upper bound, or None for "up to now".

    Returns:
        A `StatisticsResult` with the resolved resolution, DataFrame, and
        the original unit_of_measurement (before conversion).
    """
    return await _async_fetch_with_unit(hass, entity_id, start_time, end_time)


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
