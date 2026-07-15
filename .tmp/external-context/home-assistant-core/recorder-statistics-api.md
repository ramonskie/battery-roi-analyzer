---
source: GitHub raw (dev branch)
library: Home Assistant Core
package: homeassistant.components.recorder
topic: statistics API (statistics_during_period, list_statistic_ids, get_last_statistics, executor pattern)
fetched: 2026-07-15T00:00:00Z
official_docs: https://developers.home-assistant.io/docs/core/entity/sensor/#long-term-statistics
source_file: https://github.com/home-assistant/core/blob/dev/homeassistant/components/recorder/statistics.py
---

# `homeassistant.components.recorder.statistics` — key functions

All functions below are **synchronous / blocking** (they open a DB session).
They must NEVER be called directly from the event loop — always via
`get_instance(hass).async_add_executor_job(...)`.

## Import
```python
from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.statistics import (
    statistics_during_period,
    list_statistic_ids,
    get_last_statistics,
    get_last_short_term_statistics,
)
```

## `statistics_during_period`

```python
def statistics_during_period(
    hass: HomeAssistant,
    start_time: datetime,
    end_time: datetime | None,
    statistic_ids: set[str] | None,
    period: Literal["5minute", "day", "hour", "week", "month", "year"],
    units: dict[str, str] | None,
    types: set[Literal["change", "last_reset", "max", "mean", "min", "state", "sum"]],
) -> dict[str, list[StatisticsRow]]:
    """Return statistic data points during UTC period start_time - end_time.

    If end_time is omitted, returns statistics newer than or equal to start_time.
    If statistic_ids is omitted, returns statistics for all statistics ids.
    """
```

### Parameters
- `start_time: datetime` — UTC datetime, inclusive lower bound.
- `end_time: datetime | None` — UTC datetime, exclusive upper bound. `None` = "everything from start_time onward".
- `statistic_ids: set[str] | None` — set of statistic IDs to filter; `None` = all known statistics. **Must be a `set`**, not a list (a list is coerced with a deprecation warning for backward compat).
- `period: Literal["5minute", "day", "hour", "week", "month", "year"]` — granularity (see "Period granularities" below).
- `units: dict[str, str] | None` — optional map of `unit_class -> desired_unit` (e.g. `{"energy": "kWh"}`) to force unit conversion; `None` = use each statistic's native/display unit.
- `types: set[Literal["change","last_reset","max","mean","min","state","sum"]]` — which columns to compute/return. `"change"` is a derived column (sum delta over period, internally requires `sum`).

### Return shape
```python
dict[str, list[StatisticsRow]]
```
Keyed by `statistic_id`. Each `StatisticsRow` is a `TypedDict`:
```python
class StatisticsRow(TypedDict, total=False):
    start: float        # unix timestamp (seconds), start of period bucket
    end: float           # unix timestamp (seconds), end of period bucket
    last_reset: float | None
    state: float | None
    sum: float | None
    min: float | None
    max: float | None
    mean: float | None
    mean_weight: float | None   # internal, stripped from statistics_during_period's final result
    change: float | None
```
Note: `statistics_during_period` pops `mean_weight` before returning (it's only used internally to reduce circular-mean stats). The raw `StatisticsRow` TypedDict does include it, but callers of `statistics_during_period` won't see it.

The websocket API layer (`websocket_api.py`) converts `start`/`end`/`last_reset` from float seconds to **integer milliseconds** before sending over the wire — the raw Python function itself returns **float seconds** (unix timestamp).

### Internal flow (implementation notes)
- Runs inside `with session_scope(hass=hass, read_only=True) as session:` then delegates to `_statistics_during_period_with_session(...)`.
- Fetches metadata via `get_instance(hass).statistics_meta_manager.get_many(session, statistic_ids=statistic_ids)`. If no metadata found → returns `{}`.
- **Period alignment**: `start_time`/`end_time` are snapped to period boundaries before querying:
  - `day`: aligned to local midnight, `end_time` bumped to next-day midnight.
  - `week`: aligned to local Monday 00:00 (ISO weekday).
  - `month`: aligned to first-of-month local midnight; `end_time` via `_find_month_end_time` (first of next month).
  - `year`: aligned to Jan 1 local midnight.
  - `5minute`/`hour`: no alignment — queried directly against the raw statistics tables.
- **Table selection**: `period == "5minute"` reads from `StatisticsShortTerm` (raw 5-min buckets); everything else (`hour`, `day`, `week`, `month`, `year`) reads from `Statistics` (hourly buckets) and is further reduced client-side.
- **Fallback/reduction behavior** — HA only *stores* two granularities in the DB: 5-minute (`StatisticsShortTerm`) and hourly (`Statistics`). `day`/`week`/`month`/`year` are NOT stored — they're computed on the fly by reducing hourly rows:
  - `_reduce_statistics_per_day` / `_per_week` / `_per_month` / `_per_year` — group hourly rows into the larger period, recomputing mean (arithmetic or circular per `mean_type`), min, max, and taking `last_reset`/`state`/`sum` from the last row of the period.
- If `"change"` is in the requested `types`, `_augment_result_with_change` runs an extra query to compute the sum delta over the period.
- Final cleanup strips the internal `mean_weight` key from every row.

## `get_last_statistics` / `get_last_short_term_statistics`

```python
def get_last_statistics(
    hass: HomeAssistant,
    number_of_stats: int,
    statistic_id: str,
    convert_units: bool,
    types: set[Literal["last_reset", "max", "mean", "min", "state", "sum"]],
) -> dict[str, list[StatisticsRow]]:
    """Return the last number_of_stats statistics for a statistic_id."""

def get_last_short_term_statistics(
    hass: HomeAssistant,
    number_of_stats: int,
    statistic_id: str,
    convert_units: bool,
    types: set[Literal["last_reset", "max", "mean", "min", "state", "sum"]],
) -> dict[str, list[StatisticsRow]]:
    """Return the last number_of_stats short term (5-min) statistics for a statistic_id."""
```

- `number_of_stats: int` — how many most-recent rows to return (ordered `start_ts DESC`, then reversed implicitly by consumers if needed — raw SQL order is descending by start).
- `statistic_id: str` — single statistic ID (not a set — unlike `statistics_during_period`).
- `convert_units: bool` — if `True`, converts values to the entity's current display unit (via `hass.states.get(statistic_id)` unit attribute); if `False`, returns raw stored (normalized) units.
- `types` — same column-selection semantics as above (no `"change"` option here).
- Returns `{}` if the statistic_id has no metadata or no rows.
- Return shape: same `dict[str, list[StatisticsRow]]`, but the dict will have **at most one key** (the queried `statistic_id`).
- `get_last_statistics` reads from `Statistics` (hourly); `get_last_short_term_statistics` reads from `StatisticsShortTerm` (5-min) — both are thin wrappers around a shared private `_get_last_statistics(...)` that just swaps the `table` argument.

## `list_statistic_ids`

```python
def list_statistic_ids(
    hass: HomeAssistant,
    statistic_ids: set[str] | None = None,
    statistic_type: Literal["mean", "sum"] | None = None,
) -> list[dict]:
    """Return all statistic_ids (or filtered one) and unit of measurement.

    Queries the database for existing statistic_ids, as well as integrations with
    a recorder platform for statistic_ids which will be added in the next statistics
    period.
    """
```

- `statistic_ids: set[str] | None` — filter to specific IDs; `None` = return all known statistic IDs.
- `statistic_type: Literal["mean","sum"] | None` — filter to only statistics that support that aggregation type (e.g. only `"sum"`-supporting stats for energy dashboards).
- Queries the DB first (via `statistics_meta_manager.get_many`), then — if some requested IDs are missing (or `statistic_ids` is `None`, meaning "give me everything") — additionally asks every recorder-platform integration for statistic_ids it *will* register in the next period (covers not-yet-compiled stats). DB results take priority over integration-declared ones on conflict.

### Return shape
```python
list[dict]
```
Each dict:
```python
{
    "statistic_id": str,
    "display_unit_of_measurement": str | None,
    "has_mean": bool,          # deprecated, kept for back-compat; True iff mean_type == ARITHMETIC
    "mean_type": StatisticMeanType,   # NONE / ARITHMETIC / CIRCULAR
    "has_sum": bool,
    "name": str | None,
    "source": str,             # e.g. "recorder" for pure DB-tracked stats, or integration domain
    "statistics_unit_of_measurement": str | None,
    "unit_class": str | None,
}
```

There is also an **async** convenience wrapper:
```python
async def async_list_statistic_ids(
    hass: HomeAssistant,
    statistic_ids: set[str] | None = None,
    statistic_type: Literal["mean", "sum"] | None = None,
) -> list[dict]:
```
This tries an in-memory metadata cache first (`statistics_meta_manager.get_from_cache_threadsafe`) and only falls back to `await instance.async_add_executor_job(list_statistic_ids, hass, statistic_ids, statistic_type)` on a cache miss — prefer this from async code over hand-rolling your own executor call.

## `statistic_id` resolution for a given `entity_id`

- For entities tracked natively by the recorder (i.e. most HA sensors with `state_class` set to `measurement`/`total`/`total_increasing`), **the `statistic_id` IS the `entity_id`** — no separate lookup/resolution step is needed. You can call `statistics_during_period(hass, start, end, {"sensor.my_power"}, ...)` directly using the entity_id as the statistic_id.
- For **external** statistics (data not backed by a live HA entity, e.g. imported utility data), the `statistic_id` has the format `<domain>:<slug>` (colon separator), validated by:
  ```python
  VALID_STATISTIC_ID = re.compile(r"^(?!.+__)(?!_)[\da-z_]+(?<!_):(?!_)[\da-z_]+(?<!_)$")
  def valid_statistic_id(statistic_id: str) -> bool: ...
  ```
  These are registered via `async_add_external_statistics`/`async_import_statistics`, not tied to any entity.
- Use `list_statistic_ids(hass)` (or `async_list_statistic_ids`) to discover/confirm which statistic_ids currently exist in the DB (or will exist next period) rather than assuming — this also tells you `has_mean`/`has_sum`/units so you know which `types` to request from `statistics_during_period`.
- `list_statistic_ids(hass, statistic_ids={entity_id})` returns an empty list if that entity has never produced statistics (e.g. `state_class` not set, or not yet compiled — compilation runs every 5 minutes).

## Period granularities & fallback behavior

| period    | stored natively? | source table         | notes |
|-----------|-------------------|-----------------------|-------|
| `5minute` | yes               | `StatisticsShortTerm` | raw compiled buckets, retained only ~10 days by default (`recorder.keep_days`... actually short-term stats have their own purge window, distinct from long-term `Statistics`) |
| `hour`    | yes               | `Statistics`          | compiled from 5-minute stats once per hour (`_compile_hourly_statistics`); kept indefinitely (not subject to recorder purge) |
| `day`     | **no** — derived  | `Statistics` + `_reduce_statistics_per_day`   | grouped/reduced from hourly rows at query time |
| `week`    | **no** — derived  | `Statistics` + `_reduce_statistics_per_week`  | grouped from hourly rows; week starts Monday (ISO) |
| `month`   | **no** — derived  | `Statistics` + `_reduce_statistics_per_month` | grouped from hourly rows; month end computed via `_find_month_end_time` |
| `year`    | **no** — derived  | `Statistics` + `_reduce_statistics_per_year`  | grouped from hourly rows |

Only `5minute` and `hour` hit the DB directly for aggregation; `day`/`week`/`month`/`year` always reduce hourly rows in Python after fetching them — there is no dedicated daily/weekly/monthly/yearly table. This means requesting a long `year` range with `period="year"` still requires scanning/fetching all matching hourly rows before reducing.

For `mean` values, reduction respects `mean_type` per statistic (`StatisticMeanType.ARITHMETIC` uses plain average; `StatisticMeanType.CIRCULAR` — e.g. wind direction in degrees — uses a weighted circular mean via `weighted_circular_mean`).

## `get_instance(hass).async_add_executor_job(...)` pattern

`get_instance(hass)` returns the running `Recorder` instance (from `homeassistant.components.recorder`). All the statistics functions above are blocking (SQLAlchemy sessions), so from async code (e.g. a websocket command handler or a coordinator's `_async_update_data`) always do:

```python
from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.statistics import statistics_during_period

async def _async_get_stats(hass, entity_id, start, end):
    return await get_instance(hass).async_add_executor_job(
        statistics_during_period,
        hass,
        start,
        end,
        {entity_id},          # statistic_ids
        "hour",                # period
        None,                   # units (no forced conversion)
        {"mean", "min", "max"}, # types
    )
```

Real-world example from HA's own websocket API (`recorder/websocket_api.py`):
```python
async def ws_handle_get_statistics_during_period(hass, connection, msg):
    ...
    connection.send_message(
        await get_instance(hass).async_add_executor_job(
            _ws_get_statistics_during_period,   # wrapper fn that also JSON-serializes in executor
            hass,
            msg["id"],
            start_time,
            end_time,
            set(msg["statistic_ids"]),
            msg.get("period"),
            msg.get("units"),
            types,
        )
    )
```
Note the common pattern: HA often wraps the raw statistics call **plus JSON serialization** in a single private function (e.g. `_ws_get_statistics_during_period`) and runs *that whole thing* in the executor, so the (possibly large) result never needs a second executor hop or blocking JSON-encode on the event loop.

For `list_statistic_ids`, prefer the async wrapper `async_list_statistic_ids(hass, ...)` which checks an in-memory cache before falling back to `instance.async_add_executor_job(list_statistic_ids, hass, statistic_ids, statistic_type)`.

`get_last_statistics` / `get_last_short_term_statistics` have no async wrapper in core — call them the same way:
```python
stats = await get_instance(hass).async_add_executor_job(
    get_last_statistics, hass, 1, "sensor.my_battery_soc", True, {"state", "sum"}
)
```

## Gotchas / integration notes
- `statistic_ids` for `statistics_during_period` must be a `set`; passing a `list` still works (auto-converted) but triggers an "unreachable"/back-compat code path — pass a `set` directly to avoid relying on that.
- Returned timestamps (`start`, `end`, `last_reset`) from the raw Python functions are **float unix seconds**, NOT `datetime` objects and NOT milliseconds — convert yourself (`datetime.fromtimestamp(row["start"], tz=timezone.utc)`) if needed. Only the websocket JSON layer converts to integer ms.
- If `statistic_ids` given to `statistics_during_period`/`list_statistic_ids` don't exist in the DB yet (e.g. entity added but recorder hasn't compiled first 5-min bucket), you'll get an empty dict/list for those IDs, not an error.
- `convert_units=True` in `get_last_statistics` looks up the *current* live `hass.states.get(statistic_id)` unit attribute to decide the target display unit — if the entity has been removed, it falls back to the statistic's stored native unit.
