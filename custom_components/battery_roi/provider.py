"""Data models for energy provider contracts.

Both fixed (scraped from comparison sites) and dynamic (from Enever API)
contracts share a common interface that ``recommendation.py`` consumes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class FixedContract:
    """A single fixed-price energy contract from a comparison site.

    All monetary values are EUR, kWh values are annual, gas in m³/year.
    """

    provider: str
    contract_name: str
    contract_duur_months: int
    vastrecht_elek_eur_per_month: float
    vastrecht_gas_eur_per_month: float
    leveringstarief_normaal_eur_per_kwh: float
    leveringstarief_dal_eur_per_kwh: float
    terugleververgoeding_eur_per_kwh: float
    cashback_eur: float = 0.0
    groene_stroom: bool = True

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FixedContract:
        """Parse a dictionary (from JSON) into a FixedContract."""
        return cls(
            provider=str(data["provider"]),
            contract_name=str(data["contract_name"]),
            contract_duur_months=int(data["contract_duur_months"]),
            vastrecht_elek_eur_per_month=float(data["vastrecht_elek_eur_per_month"]),
            vastrecht_gas_eur_per_month=float(data["vastrecht_gas_eur_per_month"]),
            leveringstarief_normaal_eur_per_kwh=float(data["leveringstarief_normaal_eur_per_kwh"]),
            leveringstarief_dal_eur_per_kwh=float(data["leveringstarief_dal_eur_per_kwh"]),
            terugleververgoeding_eur_per_kwh=float(data["terugleververgoeding_eur_per_kwh"]),
            cashback_eur=float(data.get("cashback_eur", 0.0)),
            groene_stroom=bool(data.get("groene_stroom", True)),
        )


@dataclass(frozen=True, slots=True)
class DynamicContract:
    """A single dynamic-price energy contract, typically from Enever API.

    All-in prices already include energy tax, VAT, and provider surcharges.
    """

    provider: str
    vastrecht_elek_eur_per_month: float
    opslag_per_kwh_eur: float
    all_in_prices: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DynamicContract:
        """Parse a dictionary into a DynamicContract."""
        return cls(
            provider=str(data["provider"]),
            vastrecht_elek_eur_per_month=float(data.get("vastrecht_elek_eur_per_month", 0.0)),
            opslag_per_kwh_eur=float(data.get("opslag_per_kwh_eur", 0.0)),
            all_in_prices=list(data.get("all_in_prices", [])),
        )

    @property
    def avg_price_eur_per_kwh(self) -> float:
        """Average all-in price per kWh over available datapoints, plus opslag."""
        if not self.all_in_prices:
            return self.opslag_per_kwh_eur
        total = sum(p.get("price", 0.0) for p in self.all_in_prices)
        return (total / len(self.all_in_prices)) + self.opslag_per_kwh_eur


@dataclass
class FixedPricesDataset:
    """Container for scraped fixed-contract data from the GitHub Action.

    ``contracts`` is the primary list consumed by ``recommendation.py``.
    """

    generated_at: datetime
    source: str
    scrape_params: dict[str, Any]
    contracts: list[FixedContract]

    @classmethod
    def from_json(cls, raw: dict[str, Any]) -> FixedPricesDataset:
        """Parse the ``fixed_prices.json`` schema into a dataset."""
        return cls(
            generated_at=datetime.fromisoformat(raw["generated_at"]),
            source=str(raw.get("source", "unknown")),
            scrape_params=dict(raw.get("scrape_params", {})),
            contracts=[FixedContract.from_dict(c) for c in raw.get("contracts", [])],
        )


@dataclass(frozen=True, slots=True)
class ProviderRecommendation:
    """A single provider's ranked recommendation with estimated annual cost."""

    provider: str
    contract_name: str
    contract_type: str  # "fixed" or "dynamic"
    estimated_annual_cost_eur: float
    estimated_annual_cost_with_battery_eur: float | None = None
    battery_capacity_kwh: float | None = None
    rank: int = 0
