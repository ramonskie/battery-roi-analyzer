"""Financial calculations for the Battery ROI Analyzer integration.

Computes ROI, net/annual savings, payback period, NPV and IRR for a
simulated battery cashflow, taking Dutch net-metering ("saldering")
scenarios into account.

NPV/IRR use ``numpy_financial`` (``npf.npv`` / ``npf.irr``). ``npf.irr``
returns ``nan`` when no real solution exists (e.g. a cashflow series that
never recoups the initial investment); this module surfaces that as
``irr_pct = None`` rather than coercing it to ``0``, so downstream
consumers (sensors) can report "unknown" instead of a misleading value.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field

import numpy_financial as npf

from .const import SalderingScenario

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class SalderingConfig:
    """Configuration for a Dutch net-metering (saldering) scenario.

    Attributes:
        scenario: Which saldering scenario to apply.
        phase_out_schedule: For ``PHASE_OUT``, a mapping of simulation
            year (1-indexed) to the fraction of exported energy still
            eligible for netting (``1.0`` == full netting, ``0.0`` ==
            no netting). Years beyond the highest key use that last
            known value. If empty and ``phase_out_years > 0``, a linear
            decline schedule is auto-generated.
        phase_out_years: Number of years over which netting linearly
            phases out (from 100% at year 1 to 0% at year N). Only
            used when ``phase_out_schedule`` is empty.
        own_tariff_eur_per_kwh: For ``OWN_TARIFF``, the custom export
            tariff to apply instead of netting. Ignored for all other
            scenarios.
        dynamic_export_prices_eur_per_kwh: For ``DYNAMIC_SENSOR``, a
            pre-resolved sequence of export prices (one entry per
            simulation year) already read from the user-supplied price
            sensor. Fetching/resolving the sensor itself is out of
            scope for this module. Ignored for all other scenarios.
    """

    scenario: SalderingScenario = SalderingScenario.NONE
    phase_out_schedule: dict[int, float] = field(default_factory=dict)
    phase_out_years: int = 0
    own_tariff_eur_per_kwh: float = 0.0
    dynamic_export_prices_eur_per_kwh: tuple[float, ...] = field(default_factory=tuple)

    def _resolve_schedule(self) -> dict[int, float]:
        """Return the effective phase-out schedule, auto-generating if needed.

        If ``phase_out_schedule`` is empty but ``phase_out_years > 0``,
        generates a linear decline: year 1 = 1.0, year N = 0.0.
        """
        if self.phase_out_schedule:
            return self.phase_out_schedule
        if self.phase_out_years > 0 and self.scenario is SalderingScenario.PHASE_OUT:
            if self.phase_out_years == 1:
                return {1: 0.0}
            divisor = self.phase_out_years - 1
            return {
                year: max(0.0, 1.0 - (year - 1) / divisor)
                for year in range(1, self.phase_out_years + 1)
            }
        return {}

    def netting_fraction_for_year(self, year: int) -> float:
        """Return the fraction of exported energy eligible for netting.

        Args:
            year: 1-indexed simulation year.

        Returns:
            ``1.0`` for ``FULL``, ``0.0`` for ``NONE``/``OWN_TARIFF``/
            ``DYNAMIC_SENSOR`` (those scenarios apply their own export
            price instead of netting), or the scheduled fraction for
            ``PHASE_OUT``.
        """
        _LOGGER.warning(
            "DEBUG netting_fraction_for_year(year=%s): scenario=%r, scenario_type=%s, "
            "phase_out_years=%s, is_FULL=%s, is_PHASE_OUT=%s, "
            "FULL_id=%s, PHASE_OUT_id=%s, self_id=%s",
            year,
            self.scenario,
            type(self.scenario).__name__,
            self.phase_out_years,
            self.scenario is SalderingScenario.FULL,
            self.scenario is SalderingScenario.PHASE_OUT,
            id(SalderingScenario.FULL),
            id(SalderingScenario.PHASE_OUT),
            id(self.scenario),
        )
        if self.scenario is SalderingScenario.FULL:
            _LOGGER.warning("DEBUG netting_fraction_for_year(year=%s): RETURNING 1.0 (FULL)", year)
            return 1.0
        if self.scenario is not SalderingScenario.PHASE_OUT:
            _LOGGER.warning("DEBUG netting_fraction_for_year(year=%s): RETURNING 0.0 (NOT PHASE_OUT)", year)
            return 0.0
        schedule = self._resolve_schedule()
        _LOGGER.warning(
            "DEBUG netting_fraction_for_year(year=%s): schedule=%s, phase_out_years=%s",
            year, schedule, self.phase_out_years,
        )
        if not schedule:
            _LOGGER.warning("DEBUG netting_fraction_for_year(year=%s): RETURNING 0.0 (empty schedule)", year)
            return 0.0
        applicable_years = [y for y in schedule if y <= year]
        if not applicable_years:
            first_year = min(schedule)
            result = schedule[first_year]
            _LOGGER.warning("DEBUG netting_fraction_for_year(year=%s): RETURNING %s (no applicable years, first_year=%s, schedule=%s)", year, result, first_year, schedule)
            return result
        result = schedule[max(applicable_years)]
        _LOGGER.warning("DEBUG netting_fraction_for_year(year=%s): RETURNING %s (max_applicable=%s, schedule=%s)", year, result, max(applicable_years), schedule)
        return result


@dataclass(frozen=True, slots=True)
class FinanceInputs:
    """User-configurable financial parameters for a ROI simulation.

    Attributes:
        import_price_eur_per_kwh: Price paid per kWh imported from the
            grid.
        export_price_eur_per_kwh: Price received per kWh exported to
            the grid (before any saldering adjustment).
        fixed_export_costs_eur_per_year: Recurring fixed costs charged
            for exporting energy (e.g. grid operator surcharges).
            Ignored under ``FULL`` netting per acceptance criteria.
        battery_price_per_kwh: Purchase price per kWh of battery capacity
            (multiplied by capacity to get total hardware cost).
        installation_costs_eur: One-off installation costs (fixed,
            independent of battery size).
        lifetime_years: Expected battery lifetime in years, used as
            the cashflow horizon for NPV/IRR/payback.
        discount_rate: Annual discount rate (interest) used for NPV,
            expressed as a fraction (e.g. ``0.05`` for 5%).
        saldering: Saldering scenario configuration.
    """

    import_price_eur_per_kwh: float
    export_price_eur_per_kwh: float
    fixed_export_costs_eur_per_year: float
    battery_price_per_kwh: float
    installation_costs_eur: float
    lifetime_years: int
    discount_rate: float
    saldering: SalderingConfig = field(default_factory=SalderingConfig)

    def __post_init__(self) -> None:
        """Validate the configured values."""
        if self.lifetime_years <= 0:
            raise ValueError("lifetime_years must be positive")
        if not -1 < self.discount_rate:
            raise ValueError("discount_rate must be greater than -1")
        if self.battery_price_per_kwh < 0 or self.installation_costs_eur < 0:
            raise ValueError("battery_price_per_kwh/installation_costs_eur must be >= 0")


@dataclass(frozen=True, slots=True)
class AnnualEnergyFlows:
    """Simulated annual energy volumes for one battery-size scenario.

    Populated by the coordinator from simulation metrics; consumed by
    :func:`_annual_cashflow` to compute savings.

    Attributes:
        imported_kwh: Grid energy imported over the year, with the
            battery in place.
        exported_kwh: Energy exported to the grid over the year, with
            the battery in place.
        baseline_imported_kwh: Grid energy that would have been
            imported without a battery (used to compute savings).
        baseline_exported_kwh: Energy that would have been exported
            without a battery. Needed to correctly compute baseline
            export revenue (the no-battery scenario also earns feed-in
            revenue, which must be subtracted from the saving).
    """

    imported_kwh: float
    exported_kwh: float
    baseline_imported_kwh: float
    baseline_exported_kwh: float = 0.0


@dataclass(frozen=True, slots=True)
class FinanceResult:
    """Financial outcome for one battery-size simulation.

    Attributes:
        battery_capacity_kwh: Battery size this result applies to.
        annual_saving_eur: Average yearly saving vs. no battery.
        net_saving_eur: Total saving over ``lifetime_years`` minus
            upfront costs (undiscounted).
        roi_pct: Return on investment as a percentage of upfront cost.
        payback_years: Years until cumulative undiscounted cashflow
            turns non-negative, or ``None`` if it never does within
            ``lifetime_years``.
        npv_eur: Net present value of the cashflow series.
        irr_pct: Internal rate of return as a percentage, or ``None``
            when ``npf.irr`` has no real solution (nan).
        cashflow_eur: The full yearly cashflow series used for
            NPV/IRR/payback (index 0 == upfront cost, negative).
    """

    battery_capacity_kwh: float
    annual_saving_eur: float
    net_saving_eur: float
    roi_pct: float
    payback_years: float | None
    npv_eur: float
    irr_pct: float | None
    cashflow_eur: tuple[float, ...]


def _export_price_for_year(
    inputs: FinanceInputs,
    year: int,
) -> float:
    """Resolve the effective export price/credit rate for a given year.

    For scenarios that use netting (``FULL``/partial via ``PHASE_OUT``),
    the netted portion of exported energy effectively earns the import
    price (it offsets an import), while the remainder earns the plain
    export price. This helper returns the *export-price* component only;
    netting is applied separately in :func:`_annual_cashflow` since it
    depends on both import and export price.
    """
    if inputs.saldering.scenario is SalderingScenario.OWN_TARIFF:
        return inputs.saldering.own_tariff_eur_per_kwh
    if inputs.saldering.scenario is SalderingScenario.DYNAMIC_SENSOR:
        prices = inputs.saldering.dynamic_export_prices_eur_per_kwh
        if not prices:
            return inputs.export_price_eur_per_kwh
        index = min(year - 1, len(prices) - 1)
        return prices[index]
    return inputs.export_price_eur_per_kwh


def _annual_cashflow(
    inputs: FinanceInputs,
    flows: AnnualEnergyFlows,
    year: int,
) -> float:
    """Compute the net cashflow (saving) for a single simulation year.

    Handles all saldering scenarios:
      * ``NONE``: exported energy is always paid at
        ``export_price_eur_per_kwh``; fixed export costs apply.
      * ``FULL``: exported energy up to the imported volume is netted
        (effectively credited at the import price); any export volume
        beyond that earns the plain export price. No fixed export
        costs are charged.
      * ``PHASE_OUT``: a declining fraction (per
        ``phase_out_schedule``) of the netting-eligible export volume
        is netted at the import price; the rest earns the plain export
        price. Fixed export costs apply on the non-netted portion.
      * ``OWN_TARIFF``: all exported energy earns a custom tariff
        instead of netting; fixed export costs apply.
      * ``DYNAMIC_SENSOR``: all exported energy earns a pre-resolved,
        per-year price from the user-supplied sensor; fixed export
        costs apply.

    Args:
        inputs: Financial configuration.
        flows: Simulated annual energy volumes for this scenario.
        year: 1-indexed simulation year (affects ``PHASE_OUT`` and
            ``DYNAMIC_SENSOR`` schedules).

    Returns:
        Net annual saving in EUR, relative to having no battery.
    """
    # --- Baseline (no battery) -------------------------------------------
    baseline_import_cost = flows.baseline_imported_kwh * inputs.import_price_eur_per_kwh

    # Baseline also earns export revenue — without accounting for it,
    # the battery scenario's export revenue is incorrectly counted as a
    # "saving" against an artificially high baseline cost.
    baseline_netting_fraction = inputs.saldering.netting_fraction_for_year(year)
    baseline_netted_kwh = flows.baseline_exported_kwh * baseline_netting_fraction
    baseline_remaining_export = flows.baseline_exported_kwh - baseline_netted_kwh
    baseline_export_revenue = (
        baseline_netted_kwh * inputs.import_price_eur_per_kwh
        + baseline_remaining_export * _export_price_for_year(inputs, year)
    )
    baseline_net_cost = baseline_import_cost - baseline_export_revenue

    # --- With battery ---------------------------------------------------
    import_cost = flows.imported_kwh * inputs.import_price_eur_per_kwh

    netting_fraction = inputs.saldering.netting_fraction_for_year(year)
    netted_kwh = flows.exported_kwh * netting_fraction
    remaining_export_kwh = flows.exported_kwh - netted_kwh

    export_price = _export_price_for_year(inputs, year)
    export_revenue = (
        netted_kwh * inputs.import_price_eur_per_kwh
        + remaining_export_kwh * export_price
    )

    fixed_export_costs = (
        0.0
        if inputs.saldering.scenario is SalderingScenario.FULL
        else inputs.fixed_export_costs_eur_per_year
    )

    battery_net_cost = import_cost - export_revenue + fixed_export_costs
    saving = baseline_net_cost - battery_net_cost
    _LOGGER.warning(
        "DEBUG _annual_cashflow(year=%s): scenario=%s, netting_fraction=%s, "
        "baseline_nf=%s, baseline_cost=%.2f, import_cost=%.2f, "
        "export_rev=%.2f, fixed_costs=%.2f, saving=%.2f, "
        "export_price=%.4f, import_price=%.4f, "
        "flows_imported=%.1f, flows_exported=%.1f, "
        "bl_import=%.1f, bl_export=%.1f",
        year,
        inputs.saldering.scenario,
        netting_fraction,
        baseline_netting_fraction,
        baseline_net_cost,
        import_cost,
        export_revenue,
        fixed_export_costs,
        saving,
        export_price,
        inputs.import_price_eur_per_kwh,
        flows.imported_kwh,
        flows.exported_kwh,
        flows.baseline_imported_kwh,
        flows.baseline_exported_kwh,
    )
    return saving


def build_cashflow_series(
    inputs: FinanceInputs,
    annual_flows: AnnualEnergyFlows,
    capacity_kwh: float = 0.0,
) -> tuple[float, ...]:
    """Build the full ``lifetime_years`` cashflow series for NPV/IRR/payback.

    The upfront cost is computed from the per-kWh battery price times the
    battery capacity, plus the fixed installation cost:
        upfront = -(price_per_kwh * capacity_kwh + installation_costs_eur)

    This makes the comparison between different battery sizes fair — a
    larger battery costs proportionally more.

    Args:
        inputs: Financial configuration.
        annual_flows: Simulated annual energy volumes for one
            battery-size scenario.
        capacity_kwh: Battery capacity used to compute total hardware cost.

    Returns:
        A tuple of length ``lifetime_years + 1`` where index 0 is the
        negative upfront cost and indices 1..N are each year's net
        saving.
    """
    upfront_cost = -(
        inputs.battery_price_per_kwh * capacity_kwh + inputs.installation_costs_eur
    )
    yearly_savings = tuple(
        _annual_cashflow(inputs, annual_flows, year)
        for year in range(1, inputs.lifetime_years + 1)
    )
    return (upfront_cost, *yearly_savings)


def calculate_payback_years(cashflow_eur: tuple[float, ...]) -> float | None:
    """Compute the payback period from a cashflow series.

    Uses linear interpolation within the year the cumulative cashflow
    crosses zero, for a more precise fractional-year estimate than a
    whole-year count.

    Args:
        cashflow_eur: Cashflow series, index 0 == upfront cost
            (negative), indices 1..N == each year's net saving.

    Returns:
        Fractional years until payback, or ``None`` if the cumulative
        cashflow never becomes non-negative within the series.
    """
    cumulative = cashflow_eur[0]
    if cumulative >= 0:
        return 0.0
    for year_index, flow in enumerate(cashflow_eur[1:], start=1):
        previous_cumulative = cumulative
        cumulative += flow
        if cumulative >= 0:
            if flow == 0:
                return float(year_index)
            fraction = -previous_cumulative / flow
            return (year_index - 1) + fraction
    return None


def calculate_npv(cashflow_eur: tuple[float, ...], discount_rate: float) -> float:
    """Calculate net present value via ``numpy_financial.npv``.

    Args:
        cashflow_eur: Cashflow series, index 0 == upfront cost.
        discount_rate: Annual discount rate (fraction, e.g. 0.05).

    Returns:
        NPV in EUR.
    """
    return float(npf.npv(discount_rate, cashflow_eur))


def calculate_irr_pct(cashflow_eur: tuple[float, ...]) -> float | None:
    """Calculate internal rate of return via ``numpy_financial.irr``.

    Args:
        cashflow_eur: Cashflow series, index 0 == upfront cost.

    Returns:
        IRR as a percentage, or ``None`` when ``npf.irr`` has no real
        solution (nan) — e.g. the investment never pays back.
    """
    irr = npf.irr(cashflow_eur)
    if irr is None or math.isnan(irr):
        return None
    return float(irr) * 100.0


def calculate_finance_result(
    battery_capacity_kwh: float,
    inputs: FinanceInputs,
    annual_flows: AnnualEnergyFlows,
) -> FinanceResult:
    """Compute the full financial result for one battery-size scenario.

    Args:
        battery_capacity_kwh: Battery size this result applies to.
        inputs: Financial configuration (prices, costs, saldering).
        annual_flows: Simulated annual energy volumes for this size.

    Returns:
        A populated :class:`FinanceResult`.
    """
    cashflow = build_cashflow_series(inputs, annual_flows, capacity_kwh=battery_capacity_kwh)
    upfront_cost = -cashflow[0]
    total_savings = sum(cashflow[1:])
    net_saving = total_savings + cashflow[0]  # cashflow[0] already negative
    annual_saving = (
        total_savings / inputs.lifetime_years if inputs.lifetime_years else 0.0
    )
    roi_pct = (net_saving / upfront_cost) * 100.0 if upfront_cost > 0 else 0.0

    return FinanceResult(
        battery_capacity_kwh=battery_capacity_kwh,
        annual_saving_eur=annual_saving,
        net_saving_eur=net_saving,
        roi_pct=roi_pct,
        payback_years=calculate_payback_years(cashflow),
        npv_eur=calculate_npv(cashflow, inputs.discount_rate),
        irr_pct=calculate_irr_pct(cashflow),
        cashflow_eur=cashflow,
    )


@dataclass(frozen=True, slots=True)
class ScenarioComparison:
    """Multi-scenario comparison output for downstream sensor/coordinator use.

    Attributes:
        results: One :class:`FinanceResult` per simulated battery size,
            in the order they were computed.
        best_by_payback: The result with the shortest payback period
            (``None`` if none of the scenarios pay back).
        best_by_npv: The result with the highest NPV.
        best_by_roi: The result with the highest ROI percentage.
    """

    results: tuple[FinanceResult, ...]
    best_by_payback: FinanceResult | None
    best_by_npv: FinanceResult | None
    best_by_roi: FinanceResult | None


def compare_battery_sizes(
    results: tuple[FinanceResult, ...],
) -> ScenarioComparison:
    """Build a :class:`ScenarioComparison` from a set of per-size results.

    Args:
        results: Financial results for each simulated battery size.

    Returns:
        A populated :class:`ScenarioComparison`. Best-by fields are
        ``None`` when ``results`` is empty (or, for ``best_by_payback``,
        when no scenario pays back within its lifetime).
    """
    if not results:
        return ScenarioComparison(
            results=(),
            best_by_payback=None,
            best_by_npv=None,
            best_by_roi=None,
        )

    payback_candidates = [r for r in results if r.payback_years is not None]
    best_by_payback = (
        min(payback_candidates, key=lambda r: r.payback_years)  # type: ignore[arg-type]
        if payback_candidates
        else None
    )
    best_by_npv = max(results, key=lambda r: r.npv_eur)
    best_by_roi = max(results, key=lambda r: r.roi_pct)

    return ScenarioComparison(
        results=results,
        best_by_payback=best_by_payback,
        best_by_npv=best_by_npv,
        best_by_roi=best_by_roi,
    )
