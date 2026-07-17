"""Constants for the Battery ROI Analyzer integration."""

from __future__ import annotations

import json
from enum import StrEnum
from pathlib import Path
from typing import Final

DOMAIN: Final = "battery_roi"

# ---------------------------------------------------------------------------
# Frontend card registration
# ---------------------------------------------------------------------------

_MANIFEST_PATH: Final = Path(__file__).parent / "manifest.json"
try:
    _manifest = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
    INTEGRATION_VERSION: Final[str] = _manifest.get("version", "0.0.0")
except (OSError, json.JSONDecodeError):
    INTEGRATION_VERSION: Final[str] = "0.0.0"

URL_BASE: Final = f"/{DOMAIN}"

JSMODULES: Final[list[dict[str, str]]] = [
    {
        "name": "Battery ROI Card",
        "filename": "battery-roi-card.js",
        "version": INTEGRATION_VERSION,
    },
]

# ---------------------------------------------------------------------------
# Default battery size options (kWh) offered during config flow / comparison
# ---------------------------------------------------------------------------
DEFAULT_BATTERY_SIZES_KWH: Final[tuple[float, ...]] = (
    2,
    5,
    7.5,
    10,
    12.5,
    15,
    20,
    25,
    30,
)


class SalderingScenario(StrEnum):
    """Dutch net-metering (saldering) scenarios supported by the simulator."""

    NONE = "none"
    FULL = "full"
    PHASE_OUT = "phase_out"
    OWN_TARIFF = "own_tariff"
    DYNAMIC_SENSOR = "dynamic_sensor"


class BatteryChemistry(StrEnum):
    """Supported battery cell chemistries."""

    LFP = "lfp"
    NMC = "nmc"


# ---------------------------------------------------------------------------
# Config entry data/option keys
# ---------------------------------------------------------------------------
CONF_IMPORT_SENSOR: Final = "import_sensor"
CONF_IMPORT_SENSOR_TARIFF_2: Final = "import_sensor_tariff_2"
CONF_EXPORT_SENSOR: Final = "export_sensor"
CONF_EXPORT_SENSOR_TARIFF_2: Final = "export_sensor_tariff_2"
CONF_PRODUCTION_SENSOR: Final = "production_sensor"
CONF_CONSUMPTION_SENSOR: Final = "consumption_sensor"

CONF_IMPORT_PRICE: Final = "import_price"
CONF_EXPORT_PRICE: Final = "export_price"
CONF_IMPORT_PRICE_ENTITY: Final = "import_price_entity"
CONF_EXPORT_PRICE_ENTITY: Final = "export_price_entity"
CONF_DYNAMIC_PRICE_SENSOR: Final = "dynamic_price_sensor"

CONF_BATTERY_CAPACITY_KWH: Final = "battery_capacity_kwh"
CONF_BATTERY_CHEMISTRY: Final = "battery_chemistry"
CONF_BATTERY_MAX_CHARGE_KW: Final = "battery_max_charge_kw"
CONF_BATTERY_MAX_DISCHARGE_KW: Final = "battery_max_discharge_kw"
CONF_BATTERY_ROUND_TRIP_EFFICIENCY: Final = "battery_round_trip_efficiency"
CONF_BATTERY_DEPTH_OF_DISCHARGE: Final = "battery_depth_of_discharge"
CONF_BATTERY_DEGRADATION_PER_YEAR: Final = "battery_degradation_per_year"
CONF_BATTERY_INSTALL_COST: Final = "battery_install_cost"
CONF_BATTERY_LIFETIME_YEARS: Final = "battery_lifetime_years"

CONF_SALDERING_SCENARIO: Final = "saldering_scenario"
CONF_SALDERING_PHASE_OUT_SCHEDULE: Final = "saldering_phase_out_schedule"
CONF_PHASE_OUT_YEARS: Final = "phase_out_years"

CONF_SIMULATION_PERIOD_DAYS: Final = "simulation_period_days"
CONF_DISCOUNT_RATE: Final = "discount_rate"

# Added for config_flow/coordinator: battery hardware purchase price and
# recurring fixed export (grid operator) surcharges consumed by
# `finance.FinanceInputs` — previously only read via `dict.get(...)` with a
# bare string literal in `coordinator.py`; formalised here as named consts.
CONF_BATTERY_PRICE: Final = "battery_price_eur"
CONF_FIXED_EXPORT_COSTS: Final = "fixed_export_costs_eur_per_year"

CONF_SALDERING_OWN_TARIFF: Final = "saldering_own_tariff_eur_per_kwh"

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
DEFAULT_ROUND_TRIP_EFFICIENCY: Final = 0.9
DEFAULT_DEPTH_OF_DISCHARGE: Final = 0.9
DEFAULT_DEGRADATION_PER_YEAR: Final = 0.02
DEFAULT_BATTERY_LIFETIME_YEARS: Final = 10
DEFAULT_SIMULATION_PERIOD_DAYS: Final = 365
DEFAULT_DISCOUNT_RATE: Final = 0.05
DEFAULT_BATTERY_PRICE: Final = 0.0
DEFAULT_FIXED_EXPORT_COSTS: Final = 0.0
DEFAULT_PHASE_OUT_YEARS: Final = 10

# ---------------------------------------------------------------------------
# Coordinator / update behaviour
# ---------------------------------------------------------------------------
SIMULATION_UPDATE_INTERVAL_HOURS: Final = 24

# ---------------------------------------------------------------------------
# Sensor entity keys
# ---------------------------------------------------------------------------
SENSOR_KEY_BEST_SIZE: Final = "best_size"
SENSOR_KEY_PAYBACK_YEARS: Final = "payback"
SENSOR_KEY_ANNUAL_SAVING: Final = "annual_saving"
SENSOR_KEY_CYCLES: Final = "cycles"
SENSOR_KEY_SELF_CONSUMPTION: Final = "self_consumption"
SENSOR_KEY_IMPORT_SAVED: Final = "import_saved"
SENSOR_KEY_EXPORT_SAVED: Final = "export_saved"
SENSOR_KEY_ROI: Final = "roi"
SENSOR_KEY_NPV: Final = "npv"
SENSOR_KEY_IRR: Final = "irr"

# ---------------------------------------------------------------------------
# Provider comparison config keys
# ---------------------------------------------------------------------------
CONF_FIXED_PRICES_URL: Final = "fixed_prices_url"
CONF_ENEVER_API_TOKEN: Final = "enever_api_token"
CONF_ANNUAL_CONSUMPTION_KWH: Final = "annual_consumption_kwh"
CONF_ANNUAL_PRODUCTION_KWH: Final = "annual_production_kwh"
CONF_HAS_GAS: Final = "has_gas"

DEFAULT_FIXED_PRICES_URL: Final = (
    "https://raw.githubusercontent.com/ramonskie/battery-roi-analyzer/main/data/fixed_prices.json"
)
DEFAULT_ANNUAL_CONSUMPTION_KWH: Final = 2500
DEFAULT_ANNUAL_PRODUCTION_KWH: Final = 0

# Provider sensor keys
SENSOR_KEY_BEST_FIXED: Final = "best_fixed"
SENSOR_KEY_BEST_DYNAMIC: Final = "best_dynamic"
SENSOR_KEY_BEST_OVERALL: Final = "best_overall"
SENSOR_KEY_CHEAPEST_IMPORT: Final = "cheapest_import"
SENSOR_KEY_CHEAPEST_EXPORT: Final = "cheapest_export"
