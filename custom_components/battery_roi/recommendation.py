"""Provider recommendation engine.

Compares fixed and dynamic contracts, optionally factoring in battery
ROI simulation context. All functions are pure — no I/O, no HA deps.
"""

from __future__ import annotations

from .provider import (
    DynamicContract,
    FixedContract,
    FixedPricesDataset,
    ProviderRecommendation,
)


def _estimate_fixed_annual_cost(
    contract: FixedContract,
    annual_consumption_kwh: float,
    annual_production_kwh: float,
    has_gas: bool,
) -> float:
    """Compute estimated annual cost for a fixed contract.

    Simplified model:
        cost = vastrecht*12 + consumption*leveringstarief
               - production*terugleververgoeding
    """
    cost = contract.vastrecht_elek_eur_per_month * 12
    cost += annual_consumption_kwh * contract.leveringstarief_normaal_eur_per_kwh
    cost -= annual_production_kwh * contract.terugleververgoeding_eur_per_kwh

    if has_gas:
        cost += contract.vastrecht_gas_eur_per_month * 12

    cost -= contract.cashback_eur
    return max(cost, 0.0)


def _estimate_fixed_annual_cost_with_battery(
    contract: FixedContract,
    annual_consumption_kwh: float,
    annual_production_kwh: float,
    battery_reduced_import_kwh: float,
    battery_extra_export_kwh: float,
    has_gas: bool,
) -> float:
    """Estimate annual cost when a battery is present.

    Battery reduces grid import and may increase export (excess stored
    energy returned to grid). Both shift which contract attributes matter
    most — terugleververgoeding becomes more important.
    """
    adjusted_consumption = max(annual_consumption_kwh - battery_reduced_import_kwh, 0.0)
    adjusted_production = annual_production_kwh + battery_extra_export_kwh

    return _estimate_fixed_annual_cost(
        contract, adjusted_consumption, adjusted_production, has_gas
    )


def _estimate_dynamic_annual_cost(
    contract: DynamicContract,
    annual_consumption_kwh: float,
    annual_production_kwh: float,
) -> float:
    """Estimate annual cost for a dynamic contract using average all-in price.
    
    Vastrecht is handled by the caller (default from fixed contracts).
    """
    cost = annual_consumption_kwh * contract.avg_price_eur_per_kwh
    # Dynamic export price: raw market price (~60% of all-in, energy tax excluded)
    export_price = contract.avg_price_eur_per_kwh * 0.55
    cost -= annual_production_kwh * export_price
    return max(cost, 0.0)


def compare_providers(
    fixed_dataset: FixedPricesDataset | None,
    dynamic_contracts: list[DynamicContract] | None,
    annual_consumption_kwh: float,
    annual_production_kwh: float,
    has_gas: bool = False,
    battery_reduced_import_kwh: float = 0.0,
    battery_extra_export_kwh: float = 0.0,
    battery_capacity_kwh: float | None = None,
) -> list[ProviderRecommendation]:
    """Compare all energy contracts and return ranked recommendations.

    Fixed contracts are scored via their published tariffs.
    Dynamic contracts use average all-in prices from Enever.

    When battery context is provided (reduced_import > 0 or
    extra_export > 0), an additional ``with_battery`` estimate is
    included in each recommendation's extra attributes.

    Args:
        fixed_dataset: Parsed fixed_prices.json dataset, or None.
        dynamic_contracts: Dynamic contracts from Enever API, or None.
        annual_consumption_kwh: User's annual electricity consumption.
        annual_production_kwh: User's annual PV production (0 if none).
        has_gas: Whether the household also uses gas.
        battery_reduced_import_kwh: Annual kWh of grid import eliminated
            by a battery (from battery-roi simulation).
        battery_extra_export_kwh: Annual kWh of additional grid export
            caused by a battery (from battery-roi simulation).
        battery_capacity_kwh: The battery capacity this context refers to,
            if any.

    Returns:
        Ranked list of ``ProviderRecommendation``, cheapest first.
    """
    recommendations: list[ProviderRecommendation] = []

    # Fixed contracts
    if fixed_dataset is not None:
        for contract in fixed_dataset.contracts:
            annual_cost = _estimate_fixed_annual_cost(
                contract, annual_consumption_kwh, annual_production_kwh, has_gas
            )
            annual_cost_with_battery: float | None = None
            if battery_reduced_import_kwh > 0 or battery_extra_export_kwh > 0:
                annual_cost_with_battery = _estimate_fixed_annual_cost_with_battery(
                    contract,
                    annual_consumption_kwh,
                    annual_production_kwh,
                    battery_reduced_import_kwh,
                    battery_extra_export_kwh,
                    has_gas,
                )
            recommendations.append(
                ProviderRecommendation(
                    provider=contract.provider,
                    contract_name=contract.contract_name,
                    contract_type="fixed",
                    estimated_annual_cost_eur=round(annual_cost, 2),
                    estimated_annual_cost_with_battery_eur=(
                        round(annual_cost_with_battery, 2)
                        if annual_cost_with_battery is not None
                        else None
                    ),
                    battery_capacity_kwh=battery_capacity_kwh,
                )
            )

    # Dynamic contracts — default vastrecht from fixed average, fallback €12/mo
    if fixed_dataset is not None and fixed_dataset.contracts:
        default_vastrecht = sum(
            c.vastrecht_elek_eur_per_month for c in fixed_dataset.contracts
        ) / len(fixed_dataset.contracts)
    else:
        default_vastrecht = 12.0

    if dynamic_contracts is not None:
        for contract in dynamic_contracts:
            vastrecht = (
                contract.vastrecht_elek_eur_per_month
                if contract.vastrecht_elek_eur_per_month > 0
                else default_vastrecht
            )
            annual_cost = _estimate_dynamic_annual_cost(
                contract, annual_consumption_kwh, annual_production_kwh
            ) + vastrecht * 12
            recommendations.append(
                ProviderRecommendation(
                    provider=contract.provider,
                    contract_name=f"Dynamisch {contract.provider}",
                    contract_type="dynamic",
                    estimated_annual_cost_eur=round(annual_cost, 2),
                    battery_capacity_kwh=battery_capacity_kwh,
                )
            )

    # Rank by annual cost ascending
    recommendations.sort(key=lambda r: r.estimated_annual_cost_eur)
    for i, rec in enumerate(recommendations):
        object.__setattr__(rec, "rank", i + 1)

    return recommendations


def best_by_type(
    recommendations: list[ProviderRecommendation],
) -> dict[str, ProviderRecommendation | None]:
    """Extract the best recommendation per contract type.

    Returns:
        Dict with keys ``best_fixed``, ``best_dynamic``, ``best_overall``.
    """
    result: dict[str, ProviderRecommendation | None] = {
        "best_fixed": None,
        "best_dynamic": None,
        "best_overall": None,
    }

    for rec in recommendations:
        if rec.contract_type == "fixed" and (
            result["best_fixed"] is None
            or rec.estimated_annual_cost_eur < result["best_fixed"].estimated_annual_cost_eur
        ):
            result["best_fixed"] = rec
        if rec.contract_type == "dynamic" and (
            result["best_dynamic"] is None
            or rec.estimated_annual_cost_eur < result["best_dynamic"].estimated_annual_cost_eur
        ):
            result["best_dynamic"] = rec

    if recommendations:
        result["best_overall"] = recommendations[0]

    return result
