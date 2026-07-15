"""Unit tests for ``custom_components.battery_roi.finance``.

Pure-logic tests — no ``hass`` fixture required.
"""

from __future__ import annotations

import math

import pytest

from custom_components.battery_roi.const import SalderingScenario
from custom_components.battery_roi.finance import (
    AnnualEnergyFlows,
    FinanceInputs,
    FinanceResult,
    SalderingConfig,
    _annual_cashflow,
    calculate_irr_pct,
    calculate_npv,
    calculate_payback_years,
    compare_battery_sizes,
)


def _make_inputs(saldering: SalderingConfig) -> FinanceInputs:
    return FinanceInputs(
        import_price_eur_per_kwh=0.3,
        export_price_eur_per_kwh=0.1,
        fixed_export_costs_eur_per_year=50.0,
        battery_price_per_kwh=1000.0,
        installation_costs_eur=0.0,
        lifetime_years=1,
        discount_rate=0.05,
        saldering=saldering,
    )


_FLOWS = AnnualEnergyFlows(
    imported_kwh=200.0, exported_kwh=300.0, baseline_imported_kwh=500.0
)


# ---------------------------------------------------------------------------
# FinanceInputs validation
# ---------------------------------------------------------------------------


class TestFinanceInputsValidation:
    def test_non_positive_lifetime_raises(self) -> None:
        with pytest.raises(ValueError, match="lifetime_years"):
            FinanceInputs(
                import_price_eur_per_kwh=0.3,
                export_price_eur_per_kwh=0.1,
                fixed_export_costs_eur_per_year=0.0,
                battery_price_per_kwh=1000.0,
                installation_costs_eur=0.0,
                lifetime_years=0,
                discount_rate=0.05,
            )

    def test_discount_rate_at_or_below_negative_one_raises(self) -> None:
        with pytest.raises(ValueError, match="discount_rate"):
            FinanceInputs(
                import_price_eur_per_kwh=0.3,
                export_price_eur_per_kwh=0.1,
                fixed_export_costs_eur_per_year=0.0,
                battery_price_per_kwh=1000.0,
                installation_costs_eur=0.0,
                lifetime_years=5,
                discount_rate=-1.0,
            )

    def test_negative_battery_price_raises(self) -> None:
        with pytest.raises(ValueError, match="battery_price_per_kwh"):
            FinanceInputs(
                import_price_eur_per_kwh=0.3,
                export_price_eur_per_kwh=0.1,
                fixed_export_costs_eur_per_year=0.0,
                battery_price_per_kwh=-1.0,
                installation_costs_eur=0.0,
                lifetime_years=5,
                discount_rate=0.05,
            )


# ---------------------------------------------------------------------------
# Saldering scenario cashflow behavior
# ---------------------------------------------------------------------------


class TestSalderingScenarioCashflow:
    """Each saldering scenario should apply its documented netting/pricing rule."""

    def test_none_scenario_pays_plain_export_price_plus_fixed_costs(self) -> None:
        inputs = _make_inputs(SalderingConfig(scenario=SalderingScenario.NONE))
        cashflow = _annual_cashflow(inputs, _FLOWS, year=1)
        # export_revenue = 300*0.1 = 30; battery_cost = 60 - 30 + 50 = 80
        # baseline_cost = 150; cashflow = 150 - 80 = 70
        assert cashflow == pytest.approx(70.0)

    def test_full_scenario_nets_at_import_price_and_waives_fixed_costs(self) -> None:
        inputs = _make_inputs(SalderingConfig(scenario=SalderingScenario.FULL))
        cashflow = _annual_cashflow(inputs, _FLOWS, year=1)
        # export_revenue = 300*0.3 = 90 (full netting); fixed=0
        # battery_cost = 60 - 90 + 0 = -30; cashflow = 150 - (-30) = 180
        assert cashflow == pytest.approx(180.0)

    def test_phase_out_scenario_applies_scheduled_fraction(self) -> None:
        inputs = _make_inputs(
            SalderingConfig(
                scenario=SalderingScenario.PHASE_OUT,
                phase_out_schedule={1: 0.5},
            )
        )
        cashflow = _annual_cashflow(inputs, _FLOWS, year=1)
        # netted=150@0.3=45, remaining=150@0.1=15 -> export_revenue=60
        # battery_cost = 60 - 60 + 50 = 50; cashflow = 150 - 50 = 100
        assert cashflow == pytest.approx(100.0)

    def test_phase_out_uses_last_scheduled_fraction_beyond_schedule(self) -> None:
        inputs = _make_inputs(
            SalderingConfig(
                scenario=SalderingScenario.PHASE_OUT,
                phase_out_schedule={1: 0.5, 3: 0.1},
            )
        )
        # Year 5 exceeds the schedule's last key (3) -> uses fraction 0.1.
        fraction = inputs.saldering.netting_fraction_for_year(5)
        assert fraction == pytest.approx(0.1)

    def test_phase_out_before_first_scheduled_year_uses_first_value(self) -> None:
        config = SalderingConfig(
            scenario=SalderingScenario.PHASE_OUT,
            phase_out_schedule={3: 0.8},
        )
        assert config.netting_fraction_for_year(1) == pytest.approx(0.8)

    def test_phase_out_without_schedule_defaults_to_zero(self) -> None:
        config = SalderingConfig(scenario=SalderingScenario.PHASE_OUT)
        assert config.netting_fraction_for_year(1) == pytest.approx(0.0)

    def test_phase_out_auto_generates_linear_schedule(self) -> None:
        """phase_out_years=5 should give year1=1.0, year3=0.5, year5=0.0."""
        config = SalderingConfig(
            scenario=SalderingScenario.PHASE_OUT, phase_out_years=5
        )
        assert config.netting_fraction_for_year(1) == pytest.approx(1.0)
        assert config.netting_fraction_for_year(3) == pytest.approx(0.5)
        assert config.netting_fraction_for_year(5) == pytest.approx(0.0)
        # Beyond schedule: last known value (0.0)
        assert config.netting_fraction_for_year(10) == pytest.approx(0.0)

    def test_phase_out_auto_schedule_one_year_edge(self) -> None:
        """phase_out_years=1 should immediately drop to 0."""
        config = SalderingConfig(
            scenario=SalderingScenario.PHASE_OUT, phase_out_years=1
        )
        assert config.netting_fraction_for_year(1) == pytest.approx(0.0)

    def test_phase_out_auto_does_not_affect_other_scenarios(self) -> None:
        """Non-PHASE_OUT scenarios ignore phase_out_years."""
        full = SalderingConfig(scenario=SalderingScenario.FULL, phase_out_years=10)
        assert full.netting_fraction_for_year(5) == pytest.approx(1.0)

        none = SalderingConfig(scenario=SalderingScenario.NONE, phase_out_years=10)
        assert none.netting_fraction_for_year(5) == pytest.approx(0.0)

    def test_phase_out_explicit_schedule_takes_precedence(self) -> None:
        """If phase_out_schedule is provided, phase_out_years is ignored."""
        config = SalderingConfig(
            scenario=SalderingScenario.PHASE_OUT,
            phase_out_schedule={1: 1.0, 2: 0.0},
            phase_out_years=10,
        )
        assert config.netting_fraction_for_year(1) == pytest.approx(1.0)
        assert config.netting_fraction_for_year(2) == pytest.approx(0.0)

    def test_own_tariff_scenario_pays_custom_tariff_on_all_export(self) -> None:
        inputs = _make_inputs(
            SalderingConfig(
                scenario=SalderingScenario.OWN_TARIFF, own_tariff_eur_per_kwh=0.2
            )
        )
        cashflow = _annual_cashflow(inputs, _FLOWS, year=1)
        # export_revenue = 300*0.2 = 60; battery_cost = 60-60+50=50
        # cashflow = 150-50 = 100
        assert cashflow == pytest.approx(100.0)

    def test_dynamic_sensor_scenario_uses_resolved_per_year_price(self) -> None:
        inputs = _make_inputs(
            SalderingConfig(
                scenario=SalderingScenario.DYNAMIC_SENSOR,
                dynamic_export_prices_eur_per_kwh=(0.15,),
            )
        )
        cashflow = _annual_cashflow(inputs, _FLOWS, year=1)
        # export_revenue = 300*0.15 = 45; battery_cost = 60-45+50=65
        # cashflow = 150-65 = 85
        assert cashflow == pytest.approx(85.0)

    def test_dynamic_sensor_clamps_to_last_available_price(self) -> None:
        inputs = _make_inputs(
            SalderingConfig(
                scenario=SalderingScenario.DYNAMIC_SENSOR,
                dynamic_export_prices_eur_per_kwh=(0.15, 0.25),
            )
        )
        # Year 5 exceeds the 2-entry price series -> clamps to index -1 (0.25).
        cashflow_year5 = _annual_cashflow(inputs, _FLOWS, year=5)
        # export_revenue = 300*0.25 = 75; battery_cost = 60-75+50=35
        # cashflow = 150-35 = 115
        assert cashflow_year5 == pytest.approx(115.0)

    def test_dynamic_sensor_falls_back_to_export_price_when_no_prices_given(
        self,
    ) -> None:
        inputs = _make_inputs(
            SalderingConfig(scenario=SalderingScenario.DYNAMIC_SENSOR)
        )
        cashflow = _annual_cashflow(inputs, _FLOWS, year=1)
        # Falls back to export_price_eur_per_kwh=0.1, same as NONE scenario.
        assert cashflow == pytest.approx(70.0)


# ---------------------------------------------------------------------------
# calculate_npv / calculate_irr_pct
# ---------------------------------------------------------------------------


class TestCalculateNpv:
    def test_npv_zero_when_return_matches_discount_rate(self) -> None:
        # -1000 today, +1100 in one year at 10% discount -> NPV == 0.
        npv = calculate_npv((-1000.0, 1100.0), discount_rate=0.10)
        assert npv == pytest.approx(0.0, abs=1e-6)

    def test_npv_positive_for_favourable_cashflow(self) -> None:
        npv = calculate_npv((-1000.0, 1200.0), discount_rate=0.05)
        assert npv > 0

    def test_npv_negative_for_unfavourable_cashflow(self) -> None:
        npv = calculate_npv((-1000.0, 100.0), discount_rate=0.05)
        assert npv < 0


class TestCalculateIrrPct:
    def test_irr_matches_known_rate(self) -> None:
        irr_pct = calculate_irr_pct((-1000.0, 1100.0))
        assert irr_pct == pytest.approx(10.0, abs=1e-6)

    def test_irr_returns_none_when_investment_never_recovers(self) -> None:
        """An all-negative-return cashflow has no real IRR solution (nan)."""
        irr_pct = calculate_irr_pct((-1000.0, -100.0, -100.0, -100.0))
        assert irr_pct is None

    def test_irr_never_returns_raw_nan(self) -> None:
        irr_pct = calculate_irr_pct((-1000.0, -50.0))
        assert irr_pct is None or not math.isnan(irr_pct)


# ---------------------------------------------------------------------------
# calculate_payback_years
# ---------------------------------------------------------------------------


class TestCalculatePaybackYears:
    def test_immediate_payback_when_upfront_non_negative(self) -> None:
        assert calculate_payback_years((0.0, 100.0)) == pytest.approx(0.0)

    def test_fractional_payback_within_a_year(self) -> None:
        # -1000 upfront, +700/yr for 2 years: crosses zero during year 2.
        payback = calculate_payback_years((-1000.0, 700.0, 700.0))
        assert payback == pytest.approx(1.0 + 300.0 / 700.0)

    def test_exact_whole_year_payback(self) -> None:
        payback = calculate_payback_years((-1000.0, 500.0, 500.0))
        assert payback == pytest.approx(2.0)

    def test_never_recovered_returns_none(self) -> None:
        """Cashflow that never turns non-negative within lifetime -> None."""
        payback = calculate_payback_years((-1000.0, 100.0, 100.0, 100.0))
        assert payback is None


# ---------------------------------------------------------------------------
# compare_battery_sizes
# ---------------------------------------------------------------------------


def _make_result(
    capacity_kwh: float,
    npv_eur: float,
    roi_pct: float,
    payback_years: float | None,
) -> FinanceResult:
    return FinanceResult(
        battery_capacity_kwh=capacity_kwh,
        annual_saving_eur=100.0,
        net_saving_eur=500.0,
        roi_pct=roi_pct,
        payback_years=payback_years,
        npv_eur=npv_eur,
        irr_pct=5.0,
        cashflow_eur=(-1000.0, 200.0, 200.0, 200.0),
    )


class TestCompareBatterySizes:
    def test_empty_results_returns_all_none(self) -> None:
        comparison = compare_battery_sizes(())
        assert comparison.results == ()
        assert comparison.best_by_payback is None
        assert comparison.best_by_npv is None
        assert comparison.best_by_roi is None

    def test_selects_best_by_each_axis_independently(self) -> None:
        small = _make_result(5.0, npv_eur=100.0, roi_pct=10.0, payback_years=8.0)
        medium = _make_result(10.0, npv_eur=500.0, roi_pct=5.0, payback_years=4.0)
        large = _make_result(15.0, npv_eur=200.0, roi_pct=20.0, payback_years=None)

        comparison = compare_battery_sizes((small, medium, large))

        assert comparison.best_by_npv is medium
        assert comparison.best_by_roi is large
        assert comparison.best_by_payback is medium

    def test_best_by_payback_none_when_none_recover(self) -> None:
        never_a = _make_result(5.0, npv_eur=-100.0, roi_pct=-5.0, payback_years=None)
        never_b = _make_result(10.0, npv_eur=-50.0, roi_pct=-1.0, payback_years=None)

        comparison = compare_battery_sizes((never_a, never_b))

        assert comparison.best_by_payback is None
        assert comparison.best_by_npv is never_b
        assert comparison.best_by_roi is never_b
