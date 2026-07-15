"""Unit tests for ``custom_components.battery_roi.simulator``.

Pure-logic tests — no ``hass`` fixture required.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from custom_components.battery_roi.const import BatteryChemistry
from custom_components.battery_roi.simulator import (
    BatteryModel,
    lfp_battery_preset,
    nmc_battery_preset,
    resample_energy_series,
    simulate_battery,
)


# ---------------------------------------------------------------------------
# BatteryModel validation
# ---------------------------------------------------------------------------


class TestBatteryModelValidation:
    """``BatteryModel.__post_init__`` should reject invalid ranges."""

    def test_negative_capacity_raises(self) -> None:
        with pytest.raises(ValueError, match="capacity_kwh"):
            BatteryModel(capacity_kwh=-1.0)

    def test_zero_capacity_raises(self) -> None:
        with pytest.raises(ValueError, match="capacity_kwh"):
            BatteryModel(capacity_kwh=0.0)

    def test_roundtrip_efficiency_zero_raises(self) -> None:
        with pytest.raises(ValueError, match="roundtrip_efficiency"):
            BatteryModel(capacity_kwh=10.0, roundtrip_efficiency=0.0)

    def test_roundtrip_efficiency_above_one_raises(self) -> None:
        with pytest.raises(ValueError, match="roundtrip_efficiency"):
            BatteryModel(capacity_kwh=10.0, roundtrip_efficiency=1.5)

    def test_min_soc_greater_than_max_soc_raises(self) -> None:
        with pytest.raises(ValueError, match="min_soc"):
            BatteryModel(capacity_kwh=10.0, min_soc=0.9, max_soc=0.5)

    def test_min_soc_equal_max_soc_raises(self) -> None:
        with pytest.raises(ValueError, match="min_soc"):
            BatteryModel(capacity_kwh=10.0, min_soc=0.5, max_soc=0.5)

    def test_min_soc_negative_raises(self) -> None:
        with pytest.raises(ValueError, match="min_soc"):
            BatteryModel(capacity_kwh=10.0, min_soc=-0.1)

    def test_max_soc_above_one_raises(self) -> None:
        with pytest.raises(ValueError, match="min_soc"):
            BatteryModel(capacity_kwh=10.0, max_soc=1.1)

    def test_start_soc_below_min_raises(self) -> None:
        with pytest.raises(ValueError, match="start_soc"):
            BatteryModel(capacity_kwh=10.0, min_soc=0.2, start_soc=0.1)

    def test_start_soc_above_max_raises(self) -> None:
        with pytest.raises(ValueError, match="start_soc"):
            BatteryModel(capacity_kwh=10.0, max_soc=0.8, start_soc=0.9)

    def test_valid_model_derives_symmetric_efficiency(self) -> None:
        battery = BatteryModel(capacity_kwh=10.0, roundtrip_efficiency=0.81)
        assert battery.charge_efficiency == pytest.approx(0.9)
        assert battery.discharge_efficiency == pytest.approx(0.9)

    def test_valid_model_defaults_power_to_1c(self) -> None:
        battery = BatteryModel(capacity_kwh=7.5)
        assert battery.max_charge_power_kw == pytest.approx(7.5)
        assert battery.max_discharge_power_kw == pytest.approx(7.5)

    def test_explicit_per_leg_efficiency_not_overridden(self) -> None:
        battery = BatteryModel(
            capacity_kwh=10.0,
            charge_efficiency=0.95,
            discharge_efficiency=0.92,
        )
        assert battery.charge_efficiency == pytest.approx(0.95)
        assert battery.discharge_efficiency == pytest.approx(0.92)


# ---------------------------------------------------------------------------
# Chemistry presets
# ---------------------------------------------------------------------------


class TestChemistryPresets:
    """LFP/NMC presets should seed chemistry-typical defaults."""

    def test_lfp_preset_chemistry_and_efficiency(self) -> None:
        battery = lfp_battery_preset(10.0)
        assert battery.chemistry is BatteryChemistry.LFP
        assert battery.roundtrip_efficiency == pytest.approx(0.95)
        assert battery.min_soc == pytest.approx(0.05)

    def test_nmc_preset_chemistry_and_efficiency(self) -> None:
        battery = nmc_battery_preset(10.0)
        assert battery.chemistry is BatteryChemistry.NMC
        assert battery.roundtrip_efficiency == pytest.approx(0.90)
        assert battery.min_soc == pytest.approx(0.15)

    def test_lfp_preset_allows_overrides(self) -> None:
        battery = lfp_battery_preset(10.0, roundtrip_efficiency=0.8)
        assert battery.roundtrip_efficiency == pytest.approx(0.8)

    def test_nmc_preset_allows_overrides(self) -> None:
        battery = nmc_battery_preset(5.0, min_soc=0.3)
        assert battery.min_soc == pytest.approx(0.3)

    def test_presets_capacity_passthrough(self) -> None:
        assert lfp_battery_preset(12.5).capacity_kwh == pytest.approx(12.5)
        assert nmc_battery_preset(12.5).capacity_kwh == pytest.approx(12.5)


# ---------------------------------------------------------------------------
# simulate_battery
# ---------------------------------------------------------------------------


class TestSimulateBattery:
    """Core charge/discharge simulation loop correctness."""

    def test_requires_datetime_index(self) -> None:
        battery = BatteryModel(capacity_kwh=5.0)
        data = pd.DataFrame(
            {"pv": [1.0, 2.0], "verbruik": [1.0, 1.0], "import": [0.0, 0.0], "export": [0.0, 1.0]}
        )
        with pytest.raises(ValueError, match="DatetimeIndex"):
            simulate_battery(data, battery)

    def test_rejects_empty_or_single_row(self) -> None:
        battery = BatteryModel(capacity_kwh=5.0)
        index = pd.date_range("2026-01-01", periods=1, freq="1h")
        data = pd.DataFrame(
            {"pv": [1.0], "verbruik": [1.0], "import": [0.0], "export": [0.0]}, index=index
        )
        with pytest.raises(ValueError, match="non-empty"):
            simulate_battery(data, battery)

    def test_surplus_charges_battery(self, sample_energy_dataframe: pd.DataFrame) -> None:
        """PV surplus (hours 0, 2) should raise SOC via the charge leg."""
        battery = BatteryModel(
            capacity_kwh=2.0,
            roundtrip_efficiency=1.0,
            min_soc=0.0,
            max_soc=1.0,
            start_soc=0.5,
            max_charge_power_kw=2.0,
            max_discharge_power_kw=2.0,
        )
        result = simulate_battery(sample_energy_dataframe, battery)

        # Hour 0: surplus=4kWh, headroom=(1-0.5)*2=1kWh -> SOC rises to full.
        assert result.soc_series.iloc[0] == pytest.approx(1.0)
        assert result.utilized_solar_kwh > 0

    def test_shortfall_discharges_battery(self, sample_energy_dataframe: pd.DataFrame) -> None:
        """Consumption shortfall (hours 1, 3) should lower SOC via discharge."""
        battery = BatteryModel(
            capacity_kwh=2.0,
            roundtrip_efficiency=1.0,
            min_soc=0.0,
            max_soc=1.0,
            start_soc=0.5,
            max_charge_power_kw=2.0,
            max_discharge_power_kw=2.0,
        )
        result = simulate_battery(sample_energy_dataframe, battery)

        # Hour 1 starts fully charged (from hour 0) and fully discharges
        # to cover the 3kWh shortfall (capped by the 2kWh available).
        assert result.soc_series.iloc[1] == pytest.approx(0.0)
        assert result.extra_self_consumption_kwh > 0

    def test_soc_stays_within_min_max_bounds(
        self, sample_energy_dataframe: pd.DataFrame
    ) -> None:
        battery = BatteryModel(
            capacity_kwh=2.0,
            roundtrip_efficiency=1.0,
            min_soc=0.1,
            max_soc=0.9,
            start_soc=0.5,
            max_charge_power_kw=10.0,
            max_discharge_power_kw=10.0,
        )
        result = simulate_battery(sample_energy_dataframe, battery)

        assert (result.soc_series >= battery.min_soc - 1e-9).all()
        assert (result.soc_series <= battery.max_soc + 1e-9).all()

    def test_cycles_per_year_sane_for_repeating_pattern(
        self, sample_energy_dataframe: pd.DataFrame
    ) -> None:
        """Fully cycling a 2kWh usable battery twice in 4h annualises predictably."""
        battery = BatteryModel(
            capacity_kwh=2.0,
            roundtrip_efficiency=1.0,
            min_soc=0.0,
            max_soc=1.0,
            start_soc=0.5,
            max_charge_power_kw=2.0,
            max_discharge_power_kw=2.0,
        )
        result = simulate_battery(sample_energy_dataframe, battery)

        n_days = (
            sample_energy_dataframe.index[-1] - sample_energy_dataframe.index[0]
        ).total_seconds() / 86400.0
        usable_capacity_kwh = (battery.max_soc - battery.min_soc) * battery.capacity_kwh
        expected_cycles_in_period = result.extra_self_consumption_kwh / usable_capacity_kwh
        expected_cycles_per_year = expected_cycles_in_period * (365.0 / n_days)

        assert result.cycles_per_year == pytest.approx(expected_cycles_per_year)
        assert result.cycles_per_year > 0

    def test_no_surplus_or_shortfall_leaves_soc_flat(self) -> None:
        """When PV exactly matches consumption, SOC never moves."""
        index = pd.date_range("2026-01-01", periods=3, freq="1h")
        data = pd.DataFrame(
            {
                "pv": [2.0, 2.0, 2.0],
                "verbruik": [2.0, 2.0, 2.0],
                "import": [0.0, 0.0, 0.0],
                "export": [0.0, 0.0, 0.0],
            },
            index=index,
        )
        battery = BatteryModel(capacity_kwh=5.0, start_soc=0.5)
        result = simulate_battery(data, battery)

        assert (result.soc_series == pytest.approx(0.5)).all()
        assert result.utilized_solar_kwh == pytest.approx(0.0)
        assert result.extra_self_consumption_kwh == pytest.approx(0.0)
        assert result.cycles_per_year == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# resample_energy_series
# ---------------------------------------------------------------------------


class TestResampleEnergySeries:
    """Gap handling: small gaps forward-filled, large gaps dropped."""

    def test_empty_dataframe_returned_unchanged(self) -> None:
        empty = pd.DataFrame(columns=["pv", "verbruik"])
        result = resample_energy_series(empty, energy_columns=("pv", "verbruik"))
        assert result.empty

    def test_energy_columns_summed_when_upsampled_to_finer_freq_not_needed(self) -> None:
        """Downsampling energy columns (kWh/interval) sums rather than averages."""
        index = pd.date_range("2026-01-01", periods=4, freq="30min")
        raw = pd.DataFrame({"pv": [1.0, 1.0, 2.0, 2.0]}, index=index)
        result = resample_energy_series(raw, energy_columns=("pv",), freq="1h")

        assert result["pv"].iloc[0] == pytest.approx(2.0)
        assert result["pv"].iloc[1] == pytest.approx(4.0)

    def test_small_gap_forward_filled(self) -> None:
        """A gap within `max_fill_periods` is forward-filled, not dropped."""
        index = pd.date_range("2026-01-01", periods=5, freq="1h")
        raw = pd.DataFrame({"pv": [1.0, 2.0, np.nan, np.nan, 5.0]}, index=index)
        result = resample_energy_series(
            raw, energy_columns=("pv",), freq="1h", max_fill_periods=2
        )

        assert len(result) == 5
        assert result["pv"].iloc[2] == pytest.approx(2.0)
        assert result["pv"].iloc[3] == pytest.approx(2.0)

    def test_large_gap_dropped_not_fabricated(self) -> None:
        """A gap exceeding `max_fill_periods` is left NaN then dropped."""
        index = pd.date_range("2026-01-01", periods=6, freq="1h")
        raw = pd.DataFrame(
            {"pv": [1.0, 2.0, np.nan, np.nan, np.nan, 5.0]}, index=index
        )
        result = resample_energy_series(
            raw, energy_columns=("pv",), freq="1h", max_fill_periods=1
        )

        # Three consecutive NaNs exceed max_fill_periods=1 -> those rows
        # (plus any row still containing the unfillable NaN) are dropped.
        assert len(result) < 6
        assert not result["pv"].isna().any()

    def test_instantaneous_columns_averaged(self) -> None:
        """Non-energy columns (e.g. power/SOC) are downsampled with mean()."""
        index = pd.date_range("2026-01-01", periods=4, freq="30min")
        raw = pd.DataFrame({"soc": [0.4, 0.6, 0.5, 0.5]}, index=index)
        result = resample_energy_series(raw, energy_columns=(), freq="1h")

        assert result["soc"].iloc[0] == pytest.approx(0.5)
        assert result["soc"].iloc[1] == pytest.approx(0.5)

    def test_result_sorted_ascending(self) -> None:
        index = pd.date_range("2026-01-01", periods=3, freq="1h")
        raw = pd.DataFrame({"pv": [1.0, 2.0, 3.0]}, index=index)
        result = resample_energy_series(raw, energy_columns=("pv",), freq="1h")
        assert result.index.is_monotonic_increasing
