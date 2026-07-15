"""Config flow for the Battery ROI Analyzer integration.

Implements a 5-step `ConfigFlow` ("sensors" -> "prices" -> "battery" ->
"sim_period" -> "results") mirrored by an `OptionsFlow` of the same shape
for post-setup editing. The options flow does not need to explicitly
trigger a coordinator recompute — `coordinator.BatteryRoiCoordinator`
already registers an `add_update_listener` in its `__init__` that calls
`async_refresh()` whenever the config entry's options change.

No actual simulation is run inside this flow; the "results" step is a
lightweight confirmation before `async_create_entry`/`async_create_entry`
(options), the real simulation happens afterwards via the coordinator.
"""

from __future__ import annotations

from typing import Any, Final

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    CONF_BATTERY_CAPACITY_KWH,
    CONF_BATTERY_CHEMISTRY,
    CONF_BATTERY_INSTALL_COST,
    CONF_BATTERY_LIFETIME_YEARS,
    CONF_BATTERY_MAX_CHARGE_KW,
    CONF_BATTERY_MAX_DISCHARGE_KW,
    CONF_BATTERY_PRICE,
    CONF_BATTERY_ROUND_TRIP_EFFICIENCY,
    CONF_CONSUMPTION_SENSOR,
    CONF_DISCOUNT_RATE,
    CONF_DYNAMIC_PRICE_SENSOR,
    CONF_EXPORT_PRICE,
    CONF_EXPORT_SENSOR,
    CONF_FIXED_EXPORT_COSTS,
    CONF_IMPORT_PRICE,
    CONF_IMPORT_SENSOR,
    CONF_PHASE_OUT_YEARS,
    CONF_PRODUCTION_SENSOR,
    CONF_SALDERING_OWN_TARIFF,
    CONF_SALDERING_SCENARIO,
    CONF_SIMULATION_PERIOD_DAYS,
    DEFAULT_BATTERY_LIFETIME_YEARS,
    DEFAULT_BATTERY_PRICE,
    DEFAULT_DISCOUNT_RATE,
    DEFAULT_FIXED_EXPORT_COSTS,
    DEFAULT_PHASE_OUT_YEARS,
    DEFAULT_ROUND_TRIP_EFFICIENCY,
    DEFAULT_SIMULATION_PERIOD_DAYS,
    DOMAIN,
    BatteryChemistry,
    SalderingScenario,
)

# Device classes/units treated as valid "energy" sensors for the required
# import/export/production/consumption selections. Statistics-tracked
# sensors are expected to report cumulative kWh (state_class
# total/total_increasing), but the config flow only checks the *unit* and
# device class here — the coordinator surfaces "no statistics data" at
# runtime if the entity turns out to have no recorder history.
_VALID_ENERGY_UNITS: Final = {"kWh", "Wh", "MWh"}
_VALID_ENERGY_DEVICE_CLASSES: Final = {"energy"}

_STEP_ORDER: Final = ("sensors", "prices", "battery", "sim_period", "results")


def _energy_entity_selector(*, optional_device_class_hint: bool = False) -> EntitySelector:
    """Build an `EntitySelector` scoped to sensor entities.

    Args:
        optional_device_class_hint: Unused placeholder for future
            device-class filtering; kept for readability at call sites.

    Returns:
        An `EntitySelector` restricted to the `sensor` domain.
    """
    return EntitySelector(EntitySelectorConfig(domain="sensor"))


def _price_number_selector(*, unit_of_measurement: str = "EUR/kWh") -> NumberSelector:
    """Build a `NumberSelector` for currency/price fields."""
    return NumberSelector(
        NumberSelectorConfig(
            mode=NumberSelectorMode.BOX,
            unit_of_measurement=unit_of_measurement,
            step="any",
        )
    )


class BatteryRoiFlowMixin:
    """Shared validation logic for `ConfigFlow` and `OptionsFlow` steps.

    Both flows walk through the same five steps with the same schemas and
    validation rules; this mixin holds that logic so it isn't duplicated.
    """

    hass: Any

    def _validate_energy_sensor(self, entity_id: str | None) -> str | None:
        """Validate that `entity_id` refers to a known, numeric energy sensor.

        Args:
            entity_id: The sensor entity id to validate, or `None` (for
                the optional production sensor).

        Returns:
            An error code suitable for `errors["base"]`/field errors, or
            `None` if the entity is valid (or was not provided and is
            optional).
        """
        if entity_id is None:
            return None

        state = self.hass.states.get(entity_id)
        if state is None:
            return "invalid_sensor"

        try:
            float(state.state)
        except (TypeError, ValueError):
            return "invalid_sensor"

        device_class = state.attributes.get("device_class")
        unit = state.attributes.get("unit_of_measurement")
        if device_class not in _VALID_ENERGY_DEVICE_CLASSES and unit not in _VALID_ENERGY_UNITS:
            return "invalid_sensor"

        return None

    def _validate_sensors_step(self, user_input: dict[str, Any]) -> dict[str, str]:
        """Validate the "sensors" step's user input.

        Returns:
            A mapping of field name -> error code, empty if valid.
        """
        errors: dict[str, str] = {}
        required_fields = (
            CONF_IMPORT_SENSOR,
            CONF_EXPORT_SENSOR,
        )
        for field_name in required_fields:
            error = self._validate_energy_sensor(user_input.get(field_name))
            if error:
                errors[field_name] = error

        for optional_field in (CONF_CONSUMPTION_SENSOR, CONF_PRODUCTION_SENSOR):
            entity_id = user_input.get(optional_field)
            if entity_id:
                error = self._validate_energy_sensor(entity_id)
                if error:
                    errors[optional_field] = error

        return errors

    @staticmethod
    def _validate_prices_step(user_input: dict[str, Any]) -> dict[str, str]:
        """Validate the "prices" step's user input."""
        errors: dict[str, str] = {}
        scenario = user_input.get(CONF_SALDERING_SCENARIO, SalderingScenario.NONE)
        if scenario == SalderingScenario.OWN_TARIFF and not user_input.get(
            CONF_SALDERING_OWN_TARIFF
        ):
            errors[CONF_SALDERING_OWN_TARIFF] = "invalid_capacity"
        if scenario == SalderingScenario.DYNAMIC_SENSOR and not user_input.get(
            CONF_DYNAMIC_PRICE_SENSOR
        ):
            errors[CONF_DYNAMIC_PRICE_SENSOR] = "invalid_sensor"
        phase_out_years = user_input.get(CONF_PHASE_OUT_YEARS)
        if phase_out_years is not None and phase_out_years < 1:
            errors[CONF_PHASE_OUT_YEARS] = "invalid_capacity"
        return errors

    @staticmethod
    def _validate_battery_step(user_input: dict[str, Any]) -> dict[str, str]:
        """Validate the "battery" step's user input."""
        errors: dict[str, str] = {}
        capacity = user_input.get(CONF_BATTERY_CAPACITY_KWH)
        if capacity is not None and capacity <= 0:
            errors[CONF_BATTERY_CAPACITY_KWH] = "invalid_capacity"

        efficiency = user_input.get(CONF_BATTERY_ROUND_TRIP_EFFICIENCY)
        if efficiency is not None and not 0 < efficiency <= 100:
            errors[CONF_BATTERY_ROUND_TRIP_EFFICIENCY] = "invalid_efficiency"

        return errors

    @staticmethod
    def _validate_sim_period_step(user_input: dict[str, Any]) -> dict[str, str]:
        """Validate the "sim_period" step's user input."""
        errors: dict[str, str] = {}
        if user_input.get(CONF_SIMULATION_PERIOD_DAYS, DEFAULT_SIMULATION_PERIOD_DAYS) <= 0:
            errors[CONF_SIMULATION_PERIOD_DAYS] = "invalid_date_range"
        if user_input.get(CONF_BATTERY_LIFETIME_YEARS, DEFAULT_BATTERY_LIFETIME_YEARS) <= 0:
            errors[CONF_BATTERY_LIFETIME_YEARS] = "invalid_capacity"
        return errors

    def _sensors_schema(self, defaults: dict[str, Any]) -> vol.Schema:
        """Build the "sensors" step's data schema."""
        return vol.Schema(
            {
                vol.Required(
                    CONF_IMPORT_SENSOR, default=defaults.get(CONF_IMPORT_SENSOR)
                ): _energy_entity_selector(),
                vol.Required(
                    CONF_EXPORT_SENSOR, default=defaults.get(CONF_EXPORT_SENSOR)
                ): _energy_entity_selector(),
                vol.Optional(
                    CONF_CONSUMPTION_SENSOR,
                    default=defaults.get(CONF_CONSUMPTION_SENSOR),
                ): _energy_entity_selector(),
                vol.Optional(
                    CONF_PRODUCTION_SENSOR,
                    default=defaults.get(CONF_PRODUCTION_SENSOR),
                ): _energy_entity_selector(),
            }
        )

    def _prices_schema(self, defaults: dict[str, Any]) -> vol.Schema:
        """Build the "prices" step's data schema."""
        return vol.Schema(
            {
                vol.Required(
                    CONF_IMPORT_PRICE, default=defaults.get(CONF_IMPORT_PRICE)
                ): _price_number_selector(),
                vol.Required(
                    CONF_EXPORT_PRICE, default=defaults.get(CONF_EXPORT_PRICE)
                ): _price_number_selector(),
                vol.Optional(
                    CONF_FIXED_EXPORT_COSTS,
                    default=defaults.get(
                        CONF_FIXED_EXPORT_COSTS, DEFAULT_FIXED_EXPORT_COSTS
                    ),
                ): _price_number_selector(unit_of_measurement="EUR/year"),
                vol.Required(
                    CONF_SALDERING_SCENARIO,
                    default=defaults.get(CONF_SALDERING_SCENARIO, SalderingScenario.NONE),
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=[scenario.value for scenario in SalderingScenario],
                        mode=SelectSelectorMode.DROPDOWN,
                        translation_key=CONF_SALDERING_SCENARIO,
                    )
                ),
                vol.Optional(
                    CONF_PHASE_OUT_YEARS,
                    default=defaults.get(CONF_PHASE_OUT_YEARS, DEFAULT_PHASE_OUT_YEARS),
                ): NumberSelector(
                    NumberSelectorConfig(
                        mode=NumberSelectorMode.BOX, unit_of_measurement="years", min=1, max=30, step=1
                    )
                ),
                vol.Optional(
                    CONF_SALDERING_OWN_TARIFF,
                    default=defaults.get(CONF_SALDERING_OWN_TARIFF),
                ): _price_number_selector(),
                vol.Optional(
                    CONF_DYNAMIC_PRICE_SENSOR,
                    default=defaults.get(CONF_DYNAMIC_PRICE_SENSOR),
                ): _energy_entity_selector(),
            }
        )

    def _battery_schema(self, defaults: dict[str, Any]) -> vol.Schema:
        """Build the "battery" step's data schema."""
        return vol.Schema(
            {
                vol.Required(
                    CONF_BATTERY_CHEMISTRY,
                    default=defaults.get(CONF_BATTERY_CHEMISTRY, BatteryChemistry.LFP),
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=[chem.value for chem in BatteryChemistry],
                        mode=SelectSelectorMode.DROPDOWN,
                        translation_key=CONF_BATTERY_CHEMISTRY,
                    )
                ),
                vol.Optional(
                    CONF_BATTERY_CAPACITY_KWH,
                    default=defaults.get(CONF_BATTERY_CAPACITY_KWH),
                ): NumberSelector(
                    NumberSelectorConfig(
                        mode=NumberSelectorMode.BOX,
                        unit_of_measurement="kWh",
                        step="any",
                        min=0,
                    )
                ),
                vol.Optional(
                    CONF_BATTERY_ROUND_TRIP_EFFICIENCY,
                    default=defaults.get(
                        CONF_BATTERY_ROUND_TRIP_EFFICIENCY,
                        DEFAULT_ROUND_TRIP_EFFICIENCY * 100,
                    ),
                ): NumberSelector(
                    NumberSelectorConfig(
                        mode=NumberSelectorMode.SLIDER,
                        unit_of_measurement="%",
                        min=1,
                        max=100,
                        step=1,
                    )
                ),
                vol.Optional(
                    CONF_BATTERY_MAX_CHARGE_KW,
                    default=defaults.get(CONF_BATTERY_MAX_CHARGE_KW),
                ): NumberSelector(
                    NumberSelectorConfig(
                        mode=NumberSelectorMode.BOX, unit_of_measurement="kW", step="any", min=0
                    )
                ),
                vol.Optional(
                    CONF_BATTERY_MAX_DISCHARGE_KW,
                    default=defaults.get(CONF_BATTERY_MAX_DISCHARGE_KW),
                ): NumberSelector(
                    NumberSelectorConfig(
                        mode=NumberSelectorMode.BOX, unit_of_measurement="kW", step="any", min=0
                    )
                ),
                vol.Optional(
                    CONF_BATTERY_PRICE,
                    default=defaults.get(CONF_BATTERY_PRICE, DEFAULT_BATTERY_PRICE),
                ): _price_number_selector(unit_of_measurement="EUR"),
                vol.Optional(
                    CONF_BATTERY_INSTALL_COST,
                    default=defaults.get(CONF_BATTERY_INSTALL_COST, 0.0),
                ): _price_number_selector(unit_of_measurement="EUR"),
            }
        )

    def _sim_period_schema(self, defaults: dict[str, Any]) -> vol.Schema:
        """Build the "sim_period" step's data schema."""
        return vol.Schema(
            {
                vol.Optional(
                    CONF_SIMULATION_PERIOD_DAYS,
                    default=defaults.get(
                        CONF_SIMULATION_PERIOD_DAYS, DEFAULT_SIMULATION_PERIOD_DAYS
                    ),
                ): NumberSelector(
                    NumberSelectorConfig(
                        mode=NumberSelectorMode.BOX, unit_of_measurement="days", min=1, step=1
                    )
                ),
                vol.Optional(
                    CONF_BATTERY_LIFETIME_YEARS,
                    default=defaults.get(
                        CONF_BATTERY_LIFETIME_YEARS, DEFAULT_BATTERY_LIFETIME_YEARS
                    ),
                ): NumberSelector(
                    NumberSelectorConfig(
                        mode=NumberSelectorMode.BOX, unit_of_measurement="years", min=1, step=1
                    )
                ),
                vol.Optional(
                    CONF_DISCOUNT_RATE,
                    default=defaults.get(CONF_DISCOUNT_RATE, DEFAULT_DISCOUNT_RATE * 100),
                ): NumberSelector(
                    NumberSelectorConfig(
                        mode=NumberSelectorMode.BOX, unit_of_measurement="%", min=0, step="any"
                    )
                ),
            }
        )


class BatteryRoiConfigFlow(ConfigFlow, BatteryRoiFlowMixin, domain=DOMAIN):
    """Handle the initial 5-step config flow for Battery ROI Analyzer."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the flow's accumulated user input across steps."""
        self._collected: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Entry point; delegates straight to the "sensors" step."""
        return await self.async_step_sensors(user_input)

    async def async_step_sensors(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 1: select import/export/production/consumption sensors."""
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = self._validate_sensors_step(user_input)
            if not errors:
                self._collected.update(user_input)
                return await self.async_step_prices()

        return self.async_show_form(
            step_id="sensors",
            data_schema=self._sensors_schema(self._collected),
            errors=errors,
        )

    async def async_step_prices(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 2: energy prices + saldering scenario."""
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = self._validate_prices_step(user_input)
            if not errors:
                self._collected.update(user_input)
                return await self.async_step_battery()

        return self.async_show_form(
            step_id="prices",
            data_schema=self._prices_schema(self._collected),
            errors=errors,
        )

    async def async_step_battery(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 3: battery chemistry + physical/cost parameters."""
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = self._validate_battery_step(user_input)
            if not errors:
                self._collected.update(user_input)
                return await self.async_step_sim_period()

        return self.async_show_form(
            step_id="battery",
            data_schema=self._battery_schema(self._collected),
            errors=errors,
        )

    async def async_step_sim_period(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 4: simulation lookback period, lifetime, discount rate."""
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = self._validate_sim_period_step(user_input)
            if not errors:
                self._collected.update(user_input)
                return await self.async_step_results()

        return self.async_show_form(
            step_id="sim_period",
            data_schema=self._sim_period_schema(self._collected),
            errors=errors,
        )

    async def async_step_results(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 5: confirm and create the config entry.

        The actual simulation is run afterwards by
        `BatteryRoiCoordinator` (via `async_config_entry_first_refresh`
        in `async_setup_entry`) — this step only finalises the collected
        configuration.
        """
        if user_input is not None:
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title="Battery ROI Analyzer", data=self._collected
            )

        await self.async_set_unique_id(
            "_".join(
                str(self._collected.get(field, ""))
                for field in (CONF_IMPORT_SENSOR, CONF_EXPORT_SENSOR, CONF_PRODUCTION_SENSOR)
            )
        )
        self._abort_if_unique_id_configured()

        return self.async_show_form(step_id="results", data_schema=vol.Schema({}))

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> BatteryRoiOptionsFlow:
        """Return this integration's options flow handler."""
        return BatteryRoiOptionsFlow()


class BatteryRoiOptionsFlow(OptionsFlow, BatteryRoiFlowMixin):
    """Handle post-setup editing of all Battery ROI Analyzer parameters.

    Mirrors `BatteryRoiConfigFlow`'s five steps. On save,
    `async_create_entry` updates `config_entry.options`, which triggers
    `BatteryRoiCoordinator`'s registered `add_update_listener` callback
    to immediately re-run the simulation (bypassing the daily interval).
    """

    def __init__(self) -> None:
        """Initialize the flow's accumulated user input across steps."""
        self._collected: dict[str, Any] = {}

    def _current_values(self) -> dict[str, Any]:
        """Merge config entry `data` + `options` as prefill defaults."""
        return {**self.config_entry.data, **self.config_entry.options, **self._collected}

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Entry point; delegates straight to the "sensors" step."""
        return await self.async_step_sensors(user_input)

    async def async_step_sensors(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 1: edit import/export/production/consumption sensors."""
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = self._validate_sensors_step(user_input)
            if not errors:
                self._collected.update(user_input)
                return await self.async_step_prices()

        return self.async_show_form(
            step_id="sensors",
            data_schema=self._sensors_schema(self._current_values()),
            errors=errors,
        )

    async def async_step_prices(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 2: edit energy prices + saldering scenario."""
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = self._validate_prices_step(user_input)
            if not errors:
                self._collected.update(user_input)
                return await self.async_step_battery()

        return self.async_show_form(
            step_id="prices",
            data_schema=self._prices_schema(self._current_values()),
            errors=errors,
        )

    async def async_step_battery(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 3: edit battery chemistry + physical/cost parameters."""
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = self._validate_battery_step(user_input)
            if not errors:
                self._collected.update(user_input)
                return await self.async_step_sim_period()

        return self.async_show_form(
            step_id="battery",
            data_schema=self._battery_schema(self._current_values()),
            errors=errors,
        )

    async def async_step_sim_period(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 4: edit simulation lookback period, lifetime, discount rate."""
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = self._validate_sim_period_step(user_input)
            if not errors:
                self._collected.update(user_input)
                return await self.async_step_results()

        return self.async_show_form(
            step_id="sim_period",
            data_schema=self._sim_period_schema(self._current_values()),
            errors=errors,
        )

    async def async_step_results(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 5: confirm and save the updated options.

        Saving triggers `BatteryRoiCoordinator._async_options_updated`
        (registered via `add_update_listener`), which calls
        `async_refresh()` to immediately recompute with the new values.
        """
        if user_input is not None:
            return self.async_create_entry(data=self._current_values())

        return self.async_show_form(step_id="results", data_schema=vol.Schema({}))
