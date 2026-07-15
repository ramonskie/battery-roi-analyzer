"""Basic config flow tests for the battery_roi integration.

Requires the ``hass`` fixture (provided by
``pytest-homeassistant-custom-component``) — unlike the pure-logic
simulator/finance tests, config flow tests exercise actual HA flow
machinery (entity lookups, form rendering, entry creation).
"""

from __future__ import annotations

from typing import Any

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.battery_roi.const import (
    CONF_BATTERY_CAPACITY_KWH,
    CONF_BATTERY_CHEMISTRY,
    CONF_BATTERY_LIFETIME_YEARS,
    CONF_BATTERY_ROUND_TRIP_EFFICIENCY,
    CONF_CONSUMPTION_SENSOR,
    CONF_DISCOUNT_RATE,
    CONF_EXPORT_PRICE,
    CONF_EXPORT_SENSOR,
    CONF_IMPORT_PRICE,
    CONF_IMPORT_SENSOR,
    CONF_SALDERING_SCENARIO,
    CONF_SIMULATION_PERIOD_DAYS,
    DOMAIN,
    BatteryChemistry,
    SalderingScenario,
)


def _register_energy_sensor(hass: HomeAssistant, entity_id: str, value: float = 100.0) -> None:
    """Register a numeric sensor entity with a valid energy unit/device class."""
    hass.states.async_set(
        entity_id,
        str(value),
        {"device_class": "energy", "unit_of_measurement": "kWh"},
    )


@pytest.fixture
def energy_sensors(hass: HomeAssistant) -> dict[str, str]:
    """Register the three required energy sensors and return their ids."""
    sensors = {
        CONF_IMPORT_SENSOR: "sensor.grid_import",
        CONF_EXPORT_SENSOR: "sensor.grid_export",
        CONF_CONSUMPTION_SENSOR: "sensor.home_consumption",
    }
    for entity_id in sensors.values():
        _register_energy_sensor(hass, entity_id)
    return sensors


async def _complete_happy_path(
    hass: HomeAssistant, energy_sensors: dict[str, str]
) -> Any:
    """Drive the full 5-step config flow with valid input and return the final result."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "sensors"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_IMPORT_SENSOR: energy_sensors[CONF_IMPORT_SENSOR],
            CONF_EXPORT_SENSOR: energy_sensors[CONF_EXPORT_SENSOR],
            CONF_CONSUMPTION_SENSOR: energy_sensors[CONF_CONSUMPTION_SENSOR],
        },
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "prices"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_IMPORT_PRICE: 0.30,
            CONF_EXPORT_PRICE: 0.10,
            CONF_SALDERING_SCENARIO: SalderingScenario.NONE.value,
        },
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "battery"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_BATTERY_CHEMISTRY: BatteryChemistry.LFP.value,
            CONF_BATTERY_CAPACITY_KWH: 10.0,
            CONF_BATTERY_ROUND_TRIP_EFFICIENCY: 95,
        },
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "sim_period"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_SIMULATION_PERIOD_DAYS: 365,
            CONF_BATTERY_LIFETIME_YEARS: 10,
            CONF_DISCOUNT_RATE: 5.0,
        },
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "results"

    return await hass.config_entries.flow.async_configure(result["flow_id"], {})


async def test_full_happy_path_creates_config_entry(
    hass: HomeAssistant, energy_sensors: dict[str, str]
) -> None:
    """Stepping through all 5 steps with valid input should create an entry."""
    result = await _complete_happy_path(hass, energy_sensors)

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Battery ROI Analyzer"
    assert result["data"][CONF_IMPORT_SENSOR] == energy_sensors[CONF_IMPORT_SENSOR]
    assert result["data"][CONF_EXPORT_SENSOR] == energy_sensors[CONF_EXPORT_SENSOR]
    assert (
        result["data"][CONF_CONSUMPTION_SENSOR]
        == energy_sensors[CONF_CONSUMPTION_SENSOR]
    )
    assert result["data"][CONF_BATTERY_CAPACITY_KWH] == pytest.approx(10.0)

    assert len(hass.config_entries.async_entries(DOMAIN)) == 1


async def test_invalid_sensor_shows_form_error(hass: HomeAssistant) -> None:
    """Selecting an entity that has no HA state should surface `invalid_sensor`."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["step_id"] == "sensors"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_IMPORT_SENSOR: "sensor.does_not_exist",
            CONF_EXPORT_SENSOR: "sensor.does_not_exist",
            CONF_CONSUMPTION_SENSOR: "sensor.does_not_exist",
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "sensors"
    assert result["errors"][CONF_IMPORT_SENSOR] == "invalid_sensor"
    assert result["errors"][CONF_EXPORT_SENSOR] == "invalid_sensor"
    assert result["errors"][CONF_CONSUMPTION_SENSOR] == "invalid_sensor"


async def test_non_numeric_sensor_state_is_invalid(hass: HomeAssistant) -> None:
    """A sensor whose state can't be parsed as a float is rejected."""
    hass.states.async_set(
        "sensor.grid_import",
        "unavailable",
        {"device_class": "energy", "unit_of_measurement": "kWh"},
    )
    hass.states.async_set(
        "sensor.grid_export", "50.0", {"device_class": "energy", "unit_of_measurement": "kWh"}
    )
    hass.states.async_set(
        "sensor.home_consumption",
        "50.0",
        {"device_class": "energy", "unit_of_measurement": "kWh"},
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_IMPORT_SENSOR: "sensor.grid_import",
            CONF_EXPORT_SENSOR: "sensor.grid_export",
            CONF_CONSUMPTION_SENSOR: "sensor.home_consumption",
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"][CONF_IMPORT_SENSOR] == "invalid_sensor"


async def test_own_tariff_scenario_requires_tariff_value(
    hass: HomeAssistant, energy_sensors: dict[str, str]
) -> None:
    """Selecting OWN_TARIFF without a tariff value should error on that field."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_IMPORT_SENSOR: energy_sensors[CONF_IMPORT_SENSOR],
            CONF_EXPORT_SENSOR: energy_sensors[CONF_EXPORT_SENSOR],
            CONF_CONSUMPTION_SENSOR: energy_sensors[CONF_CONSUMPTION_SENSOR],
        },
    )
    assert result["step_id"] == "prices"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_IMPORT_PRICE: 0.30,
            CONF_EXPORT_PRICE: 0.10,
            CONF_SALDERING_SCENARIO: SalderingScenario.OWN_TARIFF.value,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "prices"
    assert "saldering_own_tariff_eur_per_kwh" in result["errors"]
