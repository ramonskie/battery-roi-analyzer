"""DataUpdateCoordinator for the Battery ROI Analyzer integration.

Fetches historical energy data via ``statistics.py``, runs the battery
sweep simulation (``simulator.py``) and the financial comparison
(``finance.py``), and caches the combined result for ``sensor.py`` to
consume.

The full simulation is CPU-heavy (numpy/pandas) and is only re-run once
per day (``SIMULATION_UPDATE_INTERVAL_HOURS``) via the coordinator's
normal polling interval, EXCEPT when the config entry's options change
(e.g. the user updates prices, battery params, or saldering scenario in
the options flow) — that triggers an immediate ``async_refresh()``,
bypassing the daily interval.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Final

import numpy as np
import pandas as pd
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_BATTERY_CAPACITY_KWH,
    CONF_BATTERY_CHEMISTRY,
    CONF_BATTERY_PRICE,
    CONF_BATTERY_DEGRADATION_PER_YEAR,
    CONF_BATTERY_DEPTH_OF_DISCHARGE,
    CONF_BATTERY_INSTALL_COST,
    CONF_BATTERY_LIFETIME_YEARS,
    CONF_BATTERY_MAX_CHARGE_KW,
    CONF_BATTERY_MAX_DISCHARGE_KW,
    CONF_BATTERY_ROUND_TRIP_EFFICIENCY,
    CONF_CONSUMPTION_SENSOR,
    CONF_DISCOUNT_RATE,
    CONF_EXPORT_PRICE,
    CONF_EXPORT_PRICE_ENTITY,
    CONF_EXPORT_SENSOR,
    CONF_EXPORT_SENSOR_TARIFF_2,
    CONF_IMPORT_PRICE,
    CONF_IMPORT_PRICE_ENTITY,
    CONF_IMPORT_SENSOR,
    CONF_IMPORT_SENSOR_TARIFF_2,
    CONF_PHASE_OUT_YEARS,
    CONF_PRODUCTION_SENSOR,
    CONF_SALDERING_PHASE_OUT_SCHEDULE,
    CONF_SALDERING_SCENARIO,
    CONF_SIMULATION_PERIOD_DAYS,
    DEFAULT_BATTERY_LIFETIME_YEARS,
    DEFAULT_BATTERY_SIZES_KWH,
    DEFAULT_DEPTH_OF_DISCHARGE,
    DEFAULT_DISCOUNT_RATE,
    DEFAULT_PHASE_OUT_YEARS,
    DEFAULT_ROUND_TRIP_EFFICIENCY,
    DEFAULT_SIMULATION_PERIOD_DAYS,
    DOMAIN,
    BatteryChemistry,
    SalderingScenario,
)
from .finance import (
    AnnualEnergyFlows,
    FinanceInputs,
    FinanceResult,
    ScenarioComparison,
    SalderingConfig,
    calculate_finance_result,
    compare_battery_sizes,
)
from .simulator import (
    BatterySimulationResult,
    resample_energy_series,
    simulate_battery_sizes,
)
from .statistics import StatisticsResult, async_get_statistics_for_entities

_LOGGER = logging.getLogger(__name__)

# Full simulation is CPU-bound (numpy/pandas), so it is only re-run at most
# once per day via the coordinator's normal polling interval. Options
# updates bypass this by calling `async_refresh()` directly (see
# `_async_options_updated`).
SIMULATION_UPDATE_INTERVAL: Final = timedelta(hours=24)

# Energy DataFrame column names expected by `simulator.simulate_battery`.
_COL_PV = "pv"
_COL_CONSUMPTION = "verbruik"
_COL_IMPORT = "import"
_COL_EXPORT = "export"


@dataclass(frozen=True, slots=True)
class BatteryRoiData:
    """Combined, cached result exposed as `coordinator.data`.

    Attributes:
        battery_results: Per-battery-size simulation results, keyed by
            capacity (kWh).
        scenario_comparison: Multi-scenario financial comparison across
            all simulated battery sizes.
        last_simulation_run: UTC timestamp of when this result was
            computed.
        monthly_data: Optional monthly-aggregated energy flows for the
            best-by-ROI capacity, used for heatmap dashboard card.
            Structured as dict of month_key -> {exported, battery_in,
            battery_out, imported} in kWh.
        by_capacity: Per-capacity breakdown of key financial + simulation
            metrics for dashboard charts. Dict of capacity_kwh ->
            {annual_saving_eur, payback_years, npv_eur, roi_pct,
             self_consumption_pct, cycles_per_year, ...}.
        annual_factor: Scale factor used to annualise raw N-day simulation
            totals (≈ 365 / n_days). ``1.0`` when a full year of data
            was available. Exposed so sensor entities can also annualise
            their values.
    """

    battery_results: dict[float, BatterySimulationResult]
    scenario_comparison: ScenarioComparison
    last_simulation_run: datetime
    monthly_data: dict[str, dict[str, float]] = field(default_factory=dict)
    by_capacity: dict[str, dict[str, float | None]] = field(default_factory=dict)
    annual_factor: float = 1.0


def _build_energy_series(result: StatisticsResult) -> pd.Series:
    """Convert statistics ``sum`` into per-period energy deltas (kWh).

    HA statistics return the ``sum`` column containing the **cumulative**
    total (not period delta) for ``total_increasing`` sensors.  We take a
    first difference to recover the per-period delta.

    The first row's delta is set to 0.0 because we lack the preceding
    cumulative value needed to compute a proper delta.

    Returns:
        A float ``Series`` of per-period kWh deltas, empty if no data.
    """
    dataframe = result.dataframe
    if dataframe.empty or "sum" not in dataframe.columns:
        return pd.Series(dtype=float)

    sums = dataframe["sum"].astype(float)
    deltas = sums.diff()
    if not deltas.empty:
        deltas.iloc[0] = 0.0
    return deltas.clip(lower=0.0)


def _build_energy_dataframe(
    stats_by_entity: dict[str, StatisticsResult],
    *,
    production_entity: str,
    consumption_entity: str | None,
    import_entity: str,
    export_entity: str,
    import_entity_tariff_2: str | None = None,
    export_entity_tariff_2: str | None = None,
) -> pd.DataFrame:
    """Assemble the combined pv/verbruik/import/export DataFrame.

    If no dedicated consumption sensor is configured, consumption is
    derived from the energy balance:
        verbruik = pv + import - export
    which holds for any grid-tied system (Kirchhoff's current law for
    energy flows).

    Dual-tariff (dal/piek) meters: pass ``import_entity_tariff_2``
    and/or ``export_entity_tariff_2`` to sum both tariffs into a single
    import/export series.

    Args:
        stats_by_entity: Mapping of entity_id -> `StatisticsResult`, as
            returned by `async_get_statistics_for_entities`.
        production_entity: Entity id configured for PV production.
        consumption_entity: Entity id configured for consumption, or
            ``None`` to derive it via energy balance.
        import_entity: Entity id configured for grid import (tariff 1).
        export_entity: Entity id configured for grid export (tariff 1).
        import_entity_tariff_2: Optional second tariff import entity.
        export_entity_tariff_2: Optional second tariff export entity.

    Returns:
        A time-indexed DataFrame with `pv`/`verbruik`/`import`/`export`
        columns, resampled to a consistent frequency and gap-filled per
        `simulator.resample_energy_series`.

    Raises:
        ValueError: If any required entity has no statistics data.
    """
    _require_entity(stats_by_entity, production_entity)
    _require_entity(stats_by_entity, import_entity)
    _require_entity(stats_by_entity, export_entity)

    pv_series = _build_energy_series(stats_by_entity[production_entity])
    import_series = _build_energy_series(stats_by_entity[import_entity])
    export_series = _build_energy_series(stats_by_entity[export_entity])

    # Sum tariff 2 into import/export when configured (dual-tariff meter)
    if import_entity_tariff_2:
        _require_entity(stats_by_entity, import_entity_tariff_2)
        import_series = import_series.add(
            _build_energy_series(stats_by_entity[import_entity_tariff_2]),
            fill_value=0.0,
        )
    if export_entity_tariff_2:
        _require_entity(stats_by_entity, export_entity_tariff_2)
        export_series = export_series.add(
            _build_energy_series(stats_by_entity[export_entity_tariff_2]),
            fill_value=0.0,
        )

    if consumption_entity:
        _require_entity(stats_by_entity, consumption_entity)
        verbruik_series = _build_energy_series(stats_by_entity[consumption_entity])
    else:
        # Derive consumption from energy balance on common index
        combined_index = (
            pv_series.index
            .union(import_series.index)
            .union(export_series.index)
            .sort_values()
        )
        pv_aligned = pv_series.reindex(combined_index).fillna(0.0)
        imp_aligned = import_series.reindex(combined_index).fillna(0.0)
        exp_aligned = export_series.reindex(combined_index).fillna(0.0)
        verbruik_series = pv_aligned + imp_aligned - exp_aligned
        verbruik_series = verbruik_series.clip(lower=0.0)

    columns: dict[str, pd.Series] = {
        _COL_PV: pv_series,
        _COL_CONSUMPTION: verbruik_series,
        _COL_IMPORT: import_series,
        _COL_EXPORT: export_series,
    }

    combined = pd.concat(columns, axis=1, join="outer").sort_index()
    return resample_energy_series(combined, energy_columns=tuple(columns))


def _require_entity(
    stats_by_entity: dict[str, StatisticsResult],
    entity_id: str,
) -> None:
    """Validate that a required entity has statistics data."""
    stats_result = stats_by_entity.get(entity_id)
    if stats_result is None:
        raise ValueError(f"No statistics fetched for configured sensor {entity_id}")
    series = _build_energy_series(stats_result)
    if series.empty:
        raise ValueError(f"No historical statistics available yet for {entity_id}")


def _build_finance_inputs(options: dict[str, Any]) -> FinanceInputs:
    """Build `FinanceInputs` from the config entry's merged data/options.

    Args:
        options: Merged config entry `data` + `options` mapping.

    Returns:
        A populated `FinanceInputs` instance.
    """
    saldering_scenario = SalderingScenario(
        options.get(CONF_SALDERING_SCENARIO, SalderingScenario.NONE)
    )
    phase_out_schedule = {
        int(year): float(fraction)
        for year, fraction in options.get(
            CONF_SALDERING_PHASE_OUT_SCHEDULE, {}
        ).items()
    }

    # Battery total price → per-kWh: user enters what they paid for their
    # specific capacity (e.g. €1800 for a 15 kWh DIY battery).  We divide
    # by the configured capacity to get a per-kWh estimate for all sizes.
    battery_capacity_kwh = float(options.get(CONF_BATTERY_CAPACITY_KWH, 1.0))
    battery_total_price = float(options.get(CONF_BATTERY_PRICE, 0.0))
    battery_price_per_kwh = (
        battery_total_price / battery_capacity_kwh
        if battery_capacity_kwh > 0
        else 0.0
    )

    return FinanceInputs(
        import_price_eur_per_kwh=float(options.get(CONF_IMPORT_PRICE, 0.0)),
        export_price_eur_per_kwh=float(options.get(CONF_EXPORT_PRICE, 0.0)),
        fixed_export_costs_eur_per_year=float(
            options.get("fixed_export_costs_eur_per_year", 0.0)
        ),
        battery_price_per_kwh=battery_price_per_kwh,
        installation_costs_eur=float(options.get(CONF_BATTERY_INSTALL_COST, 0.0)),
        lifetime_years=int(
            options.get(CONF_BATTERY_LIFETIME_YEARS, DEFAULT_BATTERY_LIFETIME_YEARS)
        ),
        discount_rate=float(options.get(CONF_DISCOUNT_RATE, DEFAULT_DISCOUNT_RATE)),
        saldering=SalderingConfig(
            scenario=saldering_scenario,
            phase_out_schedule=phase_out_schedule,
            phase_out_years=int(options.get(CONF_PHASE_OUT_YEARS, DEFAULT_PHASE_OUT_YEARS)),
        ),
    )


def _run_simulation_and_finance(
    energy_data: pd.DataFrame,
    chemistry: BatteryChemistry,
    battery_overrides: dict[str, Any],
    finance_inputs: FinanceInputs,
    annual_factor: float,
) -> tuple[dict[float, BatterySimulationResult], ScenarioComparison]:
    """Run the battery sweep + financial comparison (blocking, CPU-bound).

    Intended to be called via `hass.async_add_executor_job` — never call
    this directly from the event loop.

    .. important::
       All energy flow totals are **annualised** (multiplied by
       ``annual_factor``) before being passed to the finance
       calculations.  This ensures annual saving / NPV / payback are
       correct regardless of how many days of historical data the
       simulation had to work with.

    Args:
        energy_data: Resampled pv/verbruik/import/export DataFrame.
        chemistry: Configured battery chemistry.
        battery_overrides: Extra `BatteryModel` field overrides applied to
            every simulated size (max charge/discharge power, round-trip
            efficiency, depth of discharge).
        finance_inputs: Financial configuration for the comparison.
        annual_factor: Scale factor to convert N-day totals to a full
            year (≈ 365 / n_days).  Passed from the coordinator so it
            stays in a single location.

    Returns:
        Tuple of (per-size simulation results, scenario comparison).
    """
    battery_results = simulate_battery_sizes(
        energy_data,
        chemistry=chemistry,
        sizes_kwh=DEFAULT_BATTERY_SIZES_KWH,
        pv_column=_COL_PV,
        consumption_column=_COL_CONSUMPTION,
        import_column=_COL_IMPORT,
        export_column=_COL_EXPORT,
        **battery_overrides,
    )

    # --- Annualisation ------------------------------------------------
    total_import_kwh = float(sum(energy_data[_COL_IMPORT])) * annual_factor
    total_export_kwh = float(sum(energy_data[_COL_EXPORT])) * annual_factor

    finance_results: list[FinanceResult] = []
    for capacity_kwh, sim_result in battery_results.items():
        annual_flows = AnnualEnergyFlows(
            imported_kwh=max(
                0.0,
                total_import_kwh - sim_result.reduced_grid_import_kwh * annual_factor,
            ),
            exported_kwh=max(
                0.0,
                total_export_kwh - sim_result.reduced_export_kwh * annual_factor,
            ),
            baseline_imported_kwh=total_import_kwh,
            baseline_exported_kwh=total_export_kwh,
        )
        finance_results.append(
            calculate_finance_result(capacity_kwh, finance_inputs, annual_flows)
        )

    scenario_comparison = compare_battery_sizes(tuple(finance_results))
    return battery_results, scenario_comparison


class BatteryRoiCoordinator(DataUpdateCoordinator[BatteryRoiData]):
    """Coordinates fetching statistics and running the ROI simulation.

    Follows the 2024.8+ pattern of passing `config_entry` to
    `DataUpdateCoordinator.__init__` and using
    `async_config_entry_first_refresh()` from `async_setup_entry`. The
    simulation itself only re-runs at most once per day
    (`update_interval`); an options-update listener triggers an immediate
    out-of-band refresh when the user changes settings.
    """

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the coordinator.

        Options-update listener is registered by
        ``__init__.async_setup_entry`` via ``entry.add_update_listener`` —
        that listener calls ``async_refresh()`` on this coordinator when
        the user saves changes in the options flow.

        Args:
            hass: The Home Assistant instance.
            config_entry: The config entry this coordinator serves.
        """
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=config_entry,
            update_interval=SIMULATION_UPDATE_INTERVAL,
        )

    async def _async_update_data(self) -> BatteryRoiData:
        """Fetch statistics and run the full simulation + finance sweep.

        Returns:
            A populated `BatteryRoiData` for `sensor.py` to consume,
            including per-capacity breakdown attributes and monthly
            aggregated data for the heatmap dashboard card.

        Raises:
            UpdateFailed: If fetching statistics or running the
                simulation/finance calculations fails for any reason.
        """
        merged_config: dict[str, Any] = {
            **self.config_entry.data,
            **self.config_entry.options,
        }

        try:
            production_entity = merged_config[CONF_PRODUCTION_SENSOR]
            import_entity = merged_config[CONF_IMPORT_SENSOR]
            export_entity = merged_config[CONF_EXPORT_SENSOR]
        except KeyError as err:
            raise UpdateFailed(f"Missing required sensor configuration: {err}") from err

        consumption_entity: str | None = merged_config.get(CONF_CONSUMPTION_SENSOR) or None
        import_entity_tariff_2: str | None = merged_config.get(CONF_IMPORT_SENSOR_TARIFF_2) or None
        export_entity_tariff_2: str | None = merged_config.get(CONF_EXPORT_SENSOR_TARIFF_2) or None

        entity_ids = {production_entity, import_entity, export_entity}
        if consumption_entity:
            entity_ids.add(consumption_entity)
        if import_entity_tariff_2:
            entity_ids.add(import_entity_tariff_2)
        if export_entity_tariff_2:
            entity_ids.add(export_entity_tariff_2)

        period_days = int(
            merged_config.get(CONF_SIMULATION_PERIOD_DAYS, DEFAULT_SIMULATION_PERIOD_DAYS)
        )
        start_time = datetime.now(timezone.utc) - timedelta(days=period_days)

        try:
            stats_by_entity = await async_get_statistics_for_entities(
                self.hass,
                entity_ids,
                start_time,
            )
        except Exception as err:  # noqa: BLE001 - surface any recorder failure
            raise UpdateFailed(f"Failed to fetch historical statistics: {err}") from err

        try:
            energy_data = _build_energy_dataframe(
                stats_by_entity,
                production_entity=production_entity,
                consumption_entity=consumption_entity,
                import_entity=import_entity,
                export_entity=export_entity,
                import_entity_tariff_2=import_entity_tariff_2,
                export_entity_tariff_2=export_entity_tariff_2,
            )
        except ValueError as err:
            raise UpdateFailed(str(err)) from err

        chemistry = BatteryChemistry(
            merged_config.get(CONF_BATTERY_CHEMISTRY, BatteryChemistry.LFP)
        )
        battery_overrides: dict[str, Any] = {}
        if CONF_BATTERY_MAX_CHARGE_KW in merged_config:
            battery_overrides["max_charge_power_kw"] = float(
                merged_config[CONF_BATTERY_MAX_CHARGE_KW]
            )
        if CONF_BATTERY_MAX_DISCHARGE_KW in merged_config:
            battery_overrides["max_discharge_power_kw"] = float(
                merged_config[CONF_BATTERY_MAX_DISCHARGE_KW]
            )
        if CONF_BATTERY_ROUND_TRIP_EFFICIENCY in merged_config:
            # Config stores efficiency as percentage (e.g. 90 = 90%).
            # BatteryModel expects decimal (0.9).
            battery_overrides["roundtrip_efficiency"] = (
                float(merged_config[CONF_BATTERY_ROUND_TRIP_EFFICIENCY]) / 100.0
            )
        if CONF_BATTERY_DEPTH_OF_DISCHARGE in merged_config:
            depth_of_discharge = float(
                merged_config.get(
                    CONF_BATTERY_DEPTH_OF_DISCHARGE, DEFAULT_DEPTH_OF_DISCHARGE
                )
            )
            battery_overrides["min_soc"] = 1 - depth_of_discharge

        # Read import/export prices from configured input_number entities.
        # Falls back to the static CONF_IMPORT_PRICE / CONF_EXPORT_PRICE values
        # stored in the config entry when no entity is configured (backward compat).
        import_price_entity = merged_config.get(CONF_IMPORT_PRICE_ENTITY)
        export_price_entity = merged_config.get(CONF_EXPORT_PRICE_ENTITY)
        if import_price_entity:
            state = self.hass.states.get(import_price_entity)
            if state is not None:
                merged_config[CONF_IMPORT_PRICE] = float(state.state)
        if export_price_entity:
            state = self.hass.states.get(export_price_entity)
            if state is not None:
                merged_config[CONF_EXPORT_PRICE] = float(state.state)

        finance_inputs = _build_finance_inputs(merged_config)

        # Compute annualisation factor from the actual data span (may be
        # much shorter than the configured simulation_period_days if the
        # sensors have limited history, e.g. recently added).
        n_days = max(
            (energy_data.index[-1] - energy_data.index[0]).total_seconds() / 86400.0,
            1.0,
        )
        annual_factor = 365.0 / n_days

        try:
            # Heavy numpy/pandas CPU work — never run on the event loop.
            battery_results, scenario_comparison = (
                await self.hass.async_add_executor_job(
                    _run_simulation_and_finance,
                    energy_data,
                    chemistry,
                    battery_overrides,
                    finance_inputs,
                    annual_factor,
                )
            )
        except Exception as err:  # noqa: BLE001 - surface any simulation failure
            raise UpdateFailed(f"Battery ROI simulation failed: {err}") from err

        # Build per-capacity breakdown for dashboard charts.
        # Simulation metrics (reduced_grid_import_kwh, etc.) are raw
        # totals over N days — annualise them so the dashboard shows
        # per-year values.
        by_capacity_dict: dict[str, dict[str, float | None]] = {}
        for capacity_kwh, sim_result in battery_results.items():
            cap_key = str(capacity_kwh).replace(".", "_")
            finance_result = next(
                (r for r in scenario_comparison.results if r.battery_capacity_kwh == capacity_kwh),
                None,
            )
            entry: dict[str, float | None] = {
                "self_consumption_pct": sim_result.self_consumption_pct,
                "cycles_per_year": sim_result.cycles_per_year,
                "extra_self_consumption_kwh": sim_result.extra_self_consumption_kwh * annual_factor,
                "reduced_grid_import_kwh": sim_result.reduced_grid_import_kwh * annual_factor,
                "reduced_export_kwh": sim_result.reduced_export_kwh * annual_factor,
                "avg_daily_utilization_kwh": sim_result.avg_daily_utilization_kwh,
            }
            if finance_result is not None:
                entry["annual_saving_eur"] = finance_result.annual_saving_eur
                entry["payback_years"] = finance_result.payback_years
                entry["npv_eur"] = finance_result.npv_eur
                entry["roi_pct"] = finance_result.roi_pct
                entry["irr_pct"] = finance_result.irr_pct
            by_capacity_dict[cap_key] = entry

        # Build monthly aggregated data for heatmap (best-by-ROI capacity)
        monthly_dict: dict[str, dict[str, float]] = {}
        best_roi = scenario_comparison.best_by_roi
        if best_roi is not None and best_roi.battery_capacity_kwh in battery_results:
            best_sim = battery_results[best_roi.battery_capacity_kwh]
            if (
                best_sim.charged_kwh_series is not None
                and best_sim.discharged_kwh_series is not None
            ):
                charging_df = pd.DataFrame({
                    "battery_in": best_sim.charged_kwh_series,
                    "battery_out": best_sim.discharged_kwh_series,
                    "import": energy_data[_COL_IMPORT],
                    "export": energy_data[_COL_EXPORT],
                    "pv": energy_data.get(_COL_PV, pd.Series(0.0, index=energy_data.index)),
                })
                charging_df.index = pd.to_datetime(charging_df.index)
                monthly_groups = charging_df.resample("ME").sum()
                for timestamp, row in monthly_groups.iterrows():
                    month_key = timestamp.strftime("%Y-%m")
                    monthly_dict[month_key] = {
                        "exported_kwh": float(max(row.get("export", 0.0), 0.0)),
                        "battery_in_kwh": float(max(row.get("battery_in", 0.0), 0.0)),
                        "battery_out_kwh": float(max(row.get("battery_out", 0.0), 0.0)),
                        "imported_kwh": float(max(row.get("import", 0.0), 0.0)),
                        "pv_kwh": float(max(row.get("pv", 0.0), 0.0)),
                    }

        return BatteryRoiData(
            battery_results=battery_results,
            scenario_comparison=scenario_comparison,
            last_simulation_run=datetime.now(timezone.utc),
            monthly_data=monthly_dict,
            by_capacity=by_capacity_dict,
            annual_factor=annual_factor,
        )
