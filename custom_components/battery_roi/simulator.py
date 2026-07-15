"""Battery simulation models for the Battery ROI Analyzer integration.

This module defines the ``BatteryModel`` dataclass, LFP/NMC preset
factories, and the numpy/pandas charge/discharge simulation loop used
to estimate self-consumption gains for a given battery size against a
raw PV production / consumption / import / export time series.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final

import numpy as np
import pandas as pd

from .const import (
    DEFAULT_BATTERY_SIZES_KWH,
    DEFAULT_DEPTH_OF_DISCHARGE,
    DEFAULT_ROUND_TRIP_EFFICIENCY,
    BatteryChemistry,
)

# Assumed nominal battery pack voltage used solely to convert simulated
# kW charge/discharge power into an illustrative current figure (amps)
# for sensors/diagnostics. Residential LFP/NMC "48V" packs are the most
# common architecture; this is a display/derived-metric assumption only
# and never affects the kWh/kW simulation math itself.
ASSUMED_NOMINAL_VOLTAGE_V: Final = 48.0

# Default resampling target frequency for raw statistics series. Hourly
# statistics are what the HA Recorder guarantees long-term retention for,
# so simulations default to this cadence unless the caller resamples the
# input DataFrame differently before calling `simulate_battery`.
DEFAULT_RESAMPLE_FREQ: Final = "1h"

# Cap on consecutive resampled periods that may be forward-filled to
# paper over small gaps in the source statistics. Longer gaps are left
# as NaN (then dropped) rather than silently fabricated — see
# resample-asfreq-energy-timeseries.md guidance on capped fill limits.
DEFAULT_MAX_FILL_PERIODS: Final = 4


@dataclass(frozen=True, slots=True)
class BatteryModel:
    """Physical/electrical characteristics of a simulated battery.

    Efficiency is modelled as a symmetric split of the round-trip
    efficiency across the charge and discharge legs (each leg is the
    square root of the round-trip value) unless explicitly overridden.
    """

    capacity_kwh: float
    chemistry: BatteryChemistry = BatteryChemistry.LFP
    roundtrip_efficiency: float = DEFAULT_ROUND_TRIP_EFFICIENCY
    charge_efficiency: float = field(default=0.0)
    discharge_efficiency: float = field(default=0.0)
    max_charge_power_kw: float = field(default=0.0)
    max_discharge_power_kw: float = field(default=0.0)
    min_soc: float = field(default=1 - DEFAULT_DEPTH_OF_DISCHARGE)
    max_soc: float = 1.0
    start_soc: float = 0.5

    def __post_init__(self) -> None:
        """Fill in derived defaults and validate the configured values."""
        if not 0 < self.capacity_kwh:
            raise ValueError("capacity_kwh must be positive")
        if not 0 < self.roundtrip_efficiency <= 1:
            raise ValueError("roundtrip_efficiency must be in (0, 1]")
        if not 0 <= self.min_soc < self.max_soc <= 1:
            raise ValueError("require 0 <= min_soc < max_soc <= 1")
        if not self.min_soc <= self.start_soc <= self.max_soc:
            raise ValueError("start_soc must be within [min_soc, max_soc]")

        # Split round-trip efficiency symmetrically across each leg
        # unless the caller supplied explicit per-leg values.
        if self.charge_efficiency <= 0:
            object.__setattr__(
                self, "charge_efficiency", self.roundtrip_efficiency**0.5
            )
        if self.discharge_efficiency <= 0:
            object.__setattr__(
                self, "discharge_efficiency", self.roundtrip_efficiency**0.5
            )

        # Default power limits to a 1C rate (kW == kWh) when unset.
        if self.max_charge_power_kw <= 0:
            object.__setattr__(self, "max_charge_power_kw", self.capacity_kwh)
        if self.max_discharge_power_kw <= 0:
            object.__setattr__(self, "max_discharge_power_kw", self.capacity_kwh)


# ---------------------------------------------------------------------------
# Chemistry presets
#
# Values are representative, commonly cited defaults for residential
# storage products and are intended as sensible starting points — every
# field remains user-overridable via keyword arguments.
# ---------------------------------------------------------------------------

_LFP_ROUND_TRIP_EFFICIENCY: float = 0.95
_LFP_DEPTH_OF_DISCHARGE: float = 0.95  # LFP tolerates deep discharge well

_NMC_ROUND_TRIP_EFFICIENCY: float = 0.90
_NMC_DEPTH_OF_DISCHARGE: float = 0.85  # NMC typically kept shallower


def lfp_battery_preset(capacity_kwh: float, **overrides: object) -> BatteryModel:
    """Build a ``BatteryModel`` seeded with LFP-typical defaults.

    Args:
        capacity_kwh: Usable battery capacity in kWh.
        **overrides: Any ``BatteryModel`` field to override the preset.

    Returns:
        A configured ``BatteryModel`` instance.
    """
    defaults: dict[str, object] = {
        "chemistry": BatteryChemistry.LFP,
        "roundtrip_efficiency": _LFP_ROUND_TRIP_EFFICIENCY,
        "min_soc": 1 - _LFP_DEPTH_OF_DISCHARGE,
    }
    defaults.update(overrides)
    return BatteryModel(capacity_kwh=capacity_kwh, **defaults)  # type: ignore[arg-type]


def nmc_battery_preset(capacity_kwh: float, **overrides: object) -> BatteryModel:
    """Build a ``BatteryModel`` seeded with NMC-typical defaults.

    Args:
        capacity_kwh: Usable battery capacity in kWh.
        **overrides: Any ``BatteryModel`` field to override the preset.

    Returns:
        A configured ``BatteryModel`` instance.
    """
    defaults: dict[str, object] = {
        "chemistry": BatteryChemistry.NMC,
        "roundtrip_efficiency": _NMC_ROUND_TRIP_EFFICIENCY,
        "min_soc": 1 - _NMC_DEPTH_OF_DISCHARGE,
    }
    defaults.update(overrides)
    return BatteryModel(capacity_kwh=capacity_kwh, **defaults)  # type: ignore[arg-type]


BATTERY_PRESET_FACTORIES: dict[
    BatteryChemistry, "callable[..., BatteryModel]"  # type: ignore[valid-type]
] = {
    BatteryChemistry.LFP: lfp_battery_preset,
    BatteryChemistry.NMC: nmc_battery_preset,
}


# ---------------------------------------------------------------------------
# Simulation result
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class BatterySimulationResult:
    """Aggregate outcome of simulating one battery size over a period.

    All energy figures are in kWh, power in kW, current in amps (derived
    via ``ASSUMED_NOMINAL_VOLTAGE_V``). ``soc_series`` retains the
    per-timestep state of charge (fraction 0-1) for charting/diagnostics.
    ``charged_kwh_series`` and ``discharged_kwh_series`` hold the
    per-timestep energy flows through the battery (kWh/period), used for
    monthly aggregation in the heatmap dashboard card.
    """

    capacity_kwh: float
    self_consumption_pct: float
    extra_self_consumption_kwh: float
    reduced_grid_import_kwh: float
    reduced_export_kwh: float
    utilized_solar_kwh: float
    avg_daily_utilization_kwh: float
    cycles_per_year: float
    avg_dod: float
    required_charge_rate_kw: float
    max_simultaneous_charge_current: float
    max_discharge_current: float
    soc_series: pd.Series
    charged_kwh_series: pd.Series | None = None
    discharged_kwh_series: pd.Series | None = None


# ---------------------------------------------------------------------------
# Resampling
# ---------------------------------------------------------------------------


def resample_energy_series(
    raw: pd.DataFrame,
    energy_columns: tuple[str, ...],
    freq: str = DEFAULT_RESAMPLE_FREQ,
    max_fill_periods: int = DEFAULT_MAX_FILL_PERIODS,
) -> pd.DataFrame:
    """Resample a raw statistics DataFrame to a consistent frequency.

    Follows the pandas guidance for energy time series: flow/energy
    columns (kWh consumed/produced in an interval) are downsampled with
    ``.sum()``; any other (instantaneous, e.g. power/SOC) columns are
    downsampled with ``.mean()``. After resampling, small gaps (up to
    ``max_fill_periods`` consecutive missing periods) are forward-filled;
    larger gaps are left as NaN and then dropped, so long outages are
    never silently fabricated into fake energy flow.

    Args:
        raw: Time-indexed (DatetimeIndex) DataFrame with at least the
            columns named in `energy_columns` (e.g. pv, verbruik/
            consumption, import, export), in kWh per source interval.
        energy_columns: Column names to treat as energy (summed) rather
            than instantaneous (averaged) quantities.
        freq: Target pandas offset alias (e.g. "1h", "15min").
        max_fill_periods: Maximum consecutive resampled periods to
            forward-fill across small gaps.

    Returns:
        A resampled DataFrame at `freq`, gaps beyond the fill limit
        dropped, sorted ascending by time.
    """
    if raw.empty:
        return raw

    energy_cols = [c for c in energy_columns if c in raw.columns]
    other_cols = [c for c in raw.columns if c not in energy_cols]

    resampled = raw.resample(freq).asfreq()  # expose true gaps first
    if energy_cols:
        resampled[energy_cols] = raw[energy_cols].resample(freq).sum()
    if other_cols:
        resampled[other_cols] = raw[other_cols].resample(freq).mean()

    filled = resampled.ffill(limit=max_fill_periods)
    return filled.dropna(how="any").sort_index()


# ---------------------------------------------------------------------------
# Charge/discharge simulation
#
# The core loop below is intentionally NOT fully vectorized: state of
# charge (SOC) at timestep t depends on SOC at t-1 (it's a running
# integral clamped by min/max SOC and per-step power limits), so each
# step's charge/discharge decision cannot be computed independently of
# its predecessor. Numpy is still used for the per-step arithmetic and
# the surrounding column math (surplus/shortfall, energy deltas) is
# vectorized; only the genuinely sequential SOC recurrence runs as a
# plain Python loop over numpy arrays (faster than iterating a
# DataFrame/Series row-by-row via .iloc).
# ---------------------------------------------------------------------------


def _simulate_soc_loop(
    surplus_kwh: np.ndarray,
    shortfall_kwh: np.ndarray,
    battery: BatteryModel,
    period_hours: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Run the sequential SOC recurrence for one battery size.

    Args:
        surplus_kwh: Per-timestep PV surplus available to charge with
            (0 where verbruik >= PV).
        shortfall_kwh: Per-timestep consumption shortfall to cover by
            discharging (0 where PV >= verbruik).
        battery: Battery physical/electrical characteristics.
        period_hours: Duration of each timestep in hours (used to convert
            kW power limits into a per-step kWh energy cap).

    Returns:
        Tuple of (soc_array, charged_kwh_array, discharged_kwh_array),
        each aligned to the input arrays. `charged_kwh`/`discharged_kwh`
        are energy actually moved into/out of the battery (pre-efficiency
        losses accounted for), i.e. usable-solar-absorbed and
        load-covered respectively.
    """
    steps = surplus_kwh.shape[0]
    soc = np.empty(steps, dtype=np.float64)
    charged = np.zeros(steps, dtype=np.float64)
    discharged = np.zeros(steps, dtype=np.float64)

    capacity = battery.capacity_kwh
    max_charge_step_kwh = battery.max_charge_power_kw * period_hours
    max_discharge_step_kwh = battery.max_discharge_power_kw * period_hours
    current_soc = battery.start_soc

    for i in range(steps):
        if surplus_kwh[i] > 0:
            headroom_kwh = (battery.max_soc - current_soc) * capacity
            step_charge_kwh = min(
                surplus_kwh[i], max_charge_step_kwh, max(headroom_kwh, 0.0)
            )
            current_soc += (step_charge_kwh * battery.charge_efficiency) / capacity
            charged[i] = step_charge_kwh
        elif shortfall_kwh[i] > 0:
            available_kwh = (current_soc - battery.min_soc) * capacity
            step_discharge_kwh = min(
                shortfall_kwh[i], max_discharge_step_kwh, max(available_kwh, 0.0)
            )
            current_soc -= step_discharge_kwh / capacity
            discharged[i] = step_discharge_kwh * battery.discharge_efficiency

        soc[i] = current_soc

    return soc, charged, discharged


def simulate_battery(
    data: pd.DataFrame,
    battery: BatteryModel,
    pv_column: str = "pv",
    consumption_column: str = "verbruik",
    import_column: str = "import",
    export_column: str = "export",
) -> BatterySimulationResult:
    """Simulate one battery size against a raw energy time series.

    For each timestep: if PV production exceeds consumption, the surplus
    charges the battery (respecting `max_charge_power_kw`, `max_soc`, and
    `charge_efficiency`); otherwise the shortfall is covered by
    discharging the battery (respecting `max_discharge_power_kw`,
    `min_soc`, and `discharge_efficiency`). Grid import/export are
    recomputed post-battery to derive the reduction metrics.

    Args:
        data: Time-indexed DataFrame (evenly spaced; resample first via
            `resample_energy_series`) with PV production, consumption,
            grid import, and grid export columns, all in kWh per period.
        battery: Battery physical/electrical characteristics to simulate.
        pv_column: Column name holding PV production (kWh/period).
        consumption_column: Column name holding consumption ("verbruik",
            kWh/period).
        import_column: Column name holding grid import (kWh/period).
        export_column: Column name holding grid export (kWh/period).

    Returns:
        A `BatterySimulationResult` with per-battery-size metrics and the
        full SOC time series.

    Raises:
        ValueError: If `data` is empty or its index is not a
            `DatetimeIndex` with at least two rows (needed to infer the
            period duration).
    """
    if data.empty or len(data) < 2:
        raise ValueError("data must be a non-empty, evenly-spaced time series")
    if not isinstance(data.index, pd.DatetimeIndex):
        raise ValueError("data must be indexed by a DatetimeIndex")

    pv = data[pv_column].to_numpy(dtype=np.float64)
    verbruik = data[consumption_column].to_numpy(dtype=np.float64)
    grid_import = data[import_column].to_numpy(dtype=np.float64)
    grid_export = data[export_column].to_numpy(dtype=np.float64)

    # Vectorized: surplus/shortfall are independent per timestep.
    surplus_kwh = np.maximum(pv - verbruik, 0.0)
    shortfall_kwh = np.maximum(verbruik - pv, 0.0)

    period_hours = (data.index[1] - data.index[0]).total_seconds() / 3600.0

    soc, charged_kwh, discharged_kwh = _simulate_soc_loop(
        surplus_kwh, shortfall_kwh, battery, period_hours
    )

    # Post-battery grid flows: charging absorbs export-bound surplus;
    # discharging offsets import-bound shortfall. Vectorized column math.
    new_export = np.maximum(grid_export - charged_kwh, 0.0)
    new_import = np.maximum(grid_import - discharged_kwh, 0.0)

    reduced_export_kwh = float(np.sum(grid_export - new_export))
    reduced_grid_import_kwh = float(np.sum(grid_import - new_import))
    utilized_solar_kwh = float(np.sum(charged_kwh))
    extra_self_consumption_kwh = float(np.sum(discharged_kwh))

    total_consumption_kwh = float(np.sum(verbruik))
    baseline_self_consumption_kwh = float(np.sum(np.minimum(pv, verbruik)))
    with_battery_self_consumption_kwh = (
        baseline_self_consumption_kwh + extra_self_consumption_kwh
    )
    self_consumption_pct = (
        (with_battery_self_consumption_kwh / total_consumption_kwh) * 100.0
        if total_consumption_kwh > 0
        else 0.0
    )

    n_days = max((data.index[-1] - data.index[0]).total_seconds() / 86400.0, 1e-9)
    avg_daily_utilization_kwh = utilized_solar_kwh / n_days

    # Cycle counting: one full equivalent cycle = throughput equal to the
    # battery's usable capacity. Use discharged energy (post-efficiency)
    # as the throughput proxy, annualised from the simulated period.
    total_discharged_kwh = float(np.sum(discharged_kwh))
    usable_capacity_kwh = (battery.max_soc - battery.min_soc) * battery.capacity_kwh
    cycles_in_period = (
        total_discharged_kwh / usable_capacity_kwh if usable_capacity_kwh > 0 else 0.0
    )
    cycles_per_year = cycles_in_period * (365.0 / n_days)

    avg_dod = float(np.mean(battery.max_soc - soc)) if steps_nonempty(soc) else 0.0

    required_charge_rate_kw = float(np.max(surplus_kwh) / period_hours) if len(
        surplus_kwh
    ) else 0.0
    max_simultaneous_charge_kw = (
        float(np.max(charged_kwh) / period_hours) if len(charged_kwh) else 0.0
    )
    max_simultaneous_discharge_kw = (
        float(np.max(discharged_kwh) / period_hours) if len(discharged_kwh) else 0.0
    )
    max_simultaneous_charge_current = (
        max_simultaneous_charge_kw * 1000.0 / ASSUMED_NOMINAL_VOLTAGE_V
    )
    max_discharge_current = (
        max_simultaneous_discharge_kw * 1000.0 / ASSUMED_NOMINAL_VOLTAGE_V
    )

    return BatterySimulationResult(
        capacity_kwh=battery.capacity_kwh,
        self_consumption_pct=self_consumption_pct,
        extra_self_consumption_kwh=extra_self_consumption_kwh,
        reduced_grid_import_kwh=reduced_grid_import_kwh,
        reduced_export_kwh=reduced_export_kwh,
        utilized_solar_kwh=utilized_solar_kwh,
        avg_daily_utilization_kwh=avg_daily_utilization_kwh,
        cycles_per_year=cycles_per_year,
        avg_dod=avg_dod,
        required_charge_rate_kw=required_charge_rate_kw,
        max_simultaneous_charge_current=max_simultaneous_charge_current,
        max_discharge_current=max_discharge_current,
        soc_series=pd.Series(soc, index=data.index, name="soc"),
        charged_kwh_series=pd.Series(charged_kwh, index=data.index, name="charged_kwh"),
        discharged_kwh_series=pd.Series(discharged_kwh, index=data.index, name="discharged_kwh"),
    )


def steps_nonempty(arr: np.ndarray) -> bool:
    """Return True if `arr` has at least one element.

    Tiny helper kept for readability at call sites that guard mean/max
    reductions against empty-array warnings.
    """
    return arr.shape[0] > 0


def simulate_battery_sizes(
    data: pd.DataFrame,
    chemistry: BatteryChemistry = BatteryChemistry.LFP,
    sizes_kwh: tuple[float, ...] = DEFAULT_BATTERY_SIZES_KWH,
    pv_column: str = "pv",
    consumption_column: str = "verbruik",
    import_column: str = "import",
    export_column: str = "export",
    **battery_overrides: object,
) -> dict[float, BatterySimulationResult]:
    """Simulate a sweep of battery sizes for the given chemistry.

    Used to determine the "best size" (e.g. highest self-consumption
    percent gain per kWh installed, or best ROI once combined with
    `finance.py`).

    Args:
        data: Time-indexed DataFrame with PV/consumption/import/export
            columns (see `simulate_battery`).
        chemistry: Battery chemistry preset to use for every size.
        sizes_kwh: Capacities (kWh) to sweep; defaults to
            `DEFAULT_BATTERY_SIZES_KWH`.
        pv_column: Column name holding PV production.
        consumption_column: Column name holding consumption.
        import_column: Column name holding grid import.
        export_column: Column name holding grid export.
        **battery_overrides: Extra `BatteryModel` fields applied to every
            simulated size (e.g. custom efficiency, power limits).

    Returns:
        Mapping of capacity_kwh -> `BatterySimulationResult`.
    """
    preset_factory = BATTERY_PRESET_FACTORIES[chemistry]
    results: dict[float, BatterySimulationResult] = {}
    for size_kwh in sizes_kwh:
        battery = preset_factory(capacity_kwh=size_kwh, **battery_overrides)
        results[size_kwh] = simulate_battery(
            data,
            battery,
            pv_column=pv_column,
            consumption_column=consumption_column,
            import_column=import_column,
            export_column=export_column,
        )
    return results
