"""Diagnostics support for the Battery ROI Analyzer integration.

Returns the config entry's `data`/`options` plus a compact summary of the
coordinator's cached `BatteryRoiData` (last simulation run, per-size
financial highlights, and the best-by-ROI/NPV/payback picks). This
integration has no API keys, tokens, or other secrets to redact — the
only privacy-sensitive values it holds are the *sensor entity ids* the
user configured (`CONF_IMPORT_SENSOR`, `CONF_EXPORT_SENSOR`,
`CONF_PRODUCTION_SENSOR`, `CONF_CONSUMPTION_SENSOR`,
`CONF_DYNAMIC_PRICE_SENSOR`), since an `entity_id` can indirectly reveal
details about a user's home (e.g. `sensor.solar_edge_inverter_123`).
Those are redacted as a precaution via `async_redact_data`, matching the
"redact anything that could identify the user or their home" guidance in
the diagnostics platform docs, even though this integration has no
traditional secrets.
"""

from __future__ import annotations

from typing import Any, Final

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_CONSUMPTION_SENSOR,
    CONF_DYNAMIC_PRICE_SENSOR,
    CONF_EXPORT_SENSOR,
    CONF_IMPORT_SENSOR,
    CONF_PRODUCTION_SENSOR,
)
from .coordinator import BatteryRoiCoordinator, BatteryRoiData
from .finance import FinanceResult

# Fields redacted from `entry.data`/`entry.options` before returning
# diagnostics. These are entity ids, not secrets, but they can indirectly
# reveal details about the user's home (e.g. device/room naming) so they
# are redacted as a precaution per HA diagnostics conventions.
TO_REDACT: Final[set[str]] = {
    CONF_IMPORT_SENSOR,
    CONF_EXPORT_SENSOR,
    CONF_PRODUCTION_SENSOR,
    CONF_CONSUMPTION_SENSOR,
    CONF_DYNAMIC_PRICE_SENSOR,
}


def _finance_result_summary(result: FinanceResult) -> dict[str, Any]:
    """Reduce a `FinanceResult` to the fields useful for diagnostics.

    Omits the full `cashflow_eur` series (verbose, low diagnostic value)
    in favour of the headline financial metrics.

    Args:
        result: The financial result to summarise.

    Returns:
        A plain dict of the result's key financial metrics.
    """
    return {
        "battery_capacity_kwh": result.battery_capacity_kwh,
        "annual_saving_eur": result.annual_saving_eur,
        "net_saving_eur": result.net_saving_eur,
        "roi_pct": result.roi_pct,
        "payback_years": result.payback_years,
        "npv_eur": result.npv_eur,
        "irr_pct": result.irr_pct,
    }


def _coordinator_data_summary(data: BatteryRoiData | None) -> dict[str, Any] | None:
    """Summarise the coordinator's cached `BatteryRoiData` for diagnostics.

    Args:
        data: The coordinator's current cached data, or `None` if no
            successful refresh has completed yet.

    Returns:
        A compact dict summary, or `None` if `data` is `None`.
    """
    if data is None:
        return None

    comparison = data.scenario_comparison
    return {
        "last_simulation_run": data.last_simulation_run.isoformat(),
        "simulated_battery_sizes_kwh": sorted(data.battery_results),
        "results": [
            _finance_result_summary(result) for result in comparison.results
        ],
        "best_by_payback": (
            _finance_result_summary(comparison.best_by_payback)
            if comparison.best_by_payback is not None
            else None
        ),
        "best_by_npv": (
            _finance_result_summary(comparison.best_by_npv)
            if comparison.best_by_npv is not None
            else None
        ),
        "best_by_roi": (
            _finance_result_summary(comparison.best_by_roi)
            if comparison.best_by_roi is not None
            else None
        ),
    }


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a Battery ROI Analyzer config entry.

    Args:
        hass: The Home Assistant instance.
        entry: The config entry to produce diagnostics for.

    Returns:
        A dict containing the redacted config entry `data`/`options` and
        a summary of the coordinator's cached simulation/finance results.
    """
    coordinator: BatteryRoiCoordinator = entry.runtime_data

    return {
        "entry_data": async_redact_data(dict(entry.data), TO_REDACT),
        "entry_options": async_redact_data(dict(entry.options), TO_REDACT),
        "coordinator_data": _coordinator_data_summary(coordinator.data),
        "last_update_success": coordinator.last_update_success,
    }
