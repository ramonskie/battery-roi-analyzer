"""Sensor platform for the Battery ROI Analyzer integration.

Exposes the coordinator's cached simulation/finance results as
`sensor.battery_roi_*` entities. All sensors are `CoordinatorEntity`
subclasses reading from `coordinator.data` (a `BatteryRoiData`); no
sensor performs its own I/O or computation.

"Best size" picks the battery capacity with the highest ROI percentage
(`scenario_comparison.best_by_roi`); "best capacity" is the alternate
recommendation with the highest NPV (`scenario_comparison.best_by_npv`).
Payback/annual saving are reported for the best-by-ROI pick. Cycles,
self-consumption, and import/export saved are per-timestep simulation
metrics (`simulator.BatterySimulationResult`) for that same best-by-ROI
capacity.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final, Mapping

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfEnergy, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import BatteryRoiCoordinator, BatteryRoiData

# Currency unit for monetary sensors. HA has no dedicated EUR constant;
# `SensorDeviceClass.MONETARY` sensors declare their currency directly
# via `native_unit_of_measurement`.
_CURRENCY_EUR: Final = "EUR"

_KEY_BEST_SIZE: Final = "best_size"
_KEY_PAYBACK: Final = "payback"
_KEY_ANNUAL_SAVING: Final = "annual_saving"
_KEY_BEST_CAPACITY: Final = "best_capacity"
_KEY_CYCLES: Final = "cycles"
_KEY_SELF_CONSUMPTION: Final = "self_consumption"
_KEY_IMPORT_SAVED: Final = "import_saved"
_KEY_EXPORT_SAVED: Final = "export_saved"


@dataclass(frozen=True, kw_only=True)
class BatteryRoiSensorDescription(SensorEntityDescription):
    """Sensor description extended with a `BatteryRoiData` value getter.

    Attributes:
        value_fn: Extracts this sensor's native value from the
            coordinator's cached `BatteryRoiData`, returning `None` when
            the underlying result is unavailable (e.g. no scenario pays
            back within the configured lifetime).
    """

    value_fn: Any = None


def _best_roi_capacity_kwh(data: BatteryRoiData) -> float | None:
    """Return the capacity_kwh of the highest-ROI scenario, if any."""
    best = data.scenario_comparison.best_by_roi
    return best.capacity_kwh if best is not None else None


def _payback_years(data: BatteryRoiData) -> float | None:
    """Return payback years for the highest-ROI scenario, if any."""
    best = data.scenario_comparison.best_by_roi
    return best.payback_years if best is not None else None


def _annual_saving_eur(data: BatteryRoiData) -> float | None:
    """Return the annual saving (EUR) for the highest-ROI scenario, if any."""
    best = data.scenario_comparison.best_by_roi
    return best.annual_saving_eur if best is not None else None


def _best_npv_capacity_kwh(data: BatteryRoiData) -> float | None:
    """Return the capacity_kwh of the highest-NPV scenario, if any."""
    best = data.scenario_comparison.best_by_npv
    return best.capacity_kwh if best is not None else None


def _best_roi_simulation(data: BatteryRoiData):  # noqa: ANN202 - internal helper
    """Return the `BatterySimulationResult` for the highest-ROI capacity."""
    capacity_kwh = _best_roi_capacity_kwh(data)
    if capacity_kwh is None:
        return None
    return data.battery_results.get(capacity_kwh)


def _cycles_per_year(data: BatteryRoiData) -> float | None:
    """Return cycles/year for the highest-ROI capacity's simulation."""
    sim = _best_roi_simulation(data)
    return sim.cycles_per_year if sim is not None else None


def _self_consumption_pct(data: BatteryRoiData) -> float | None:
    """Return self-consumption % for the highest-ROI capacity's simulation."""
    sim = _best_roi_simulation(data)
    return sim.self_consumption_pct if sim is not None else None


def _import_saved_kwh(data: BatteryRoiData) -> float | None:
    """Return reduced grid import (kWh) for the highest-ROI capacity."""
    sim = _best_roi_simulation(data)
    return sim.reduced_grid_import_kwh if sim is not None else None


def _export_saved_kwh(data: BatteryRoiData) -> float | None:
    """Return reduced grid export (kWh) for the highest-ROI capacity."""
    sim = _best_roi_simulation(data)
    return sim.reduced_export_kwh if sim is not None else None


SENSOR_DESCRIPTIONS: Final[tuple[BatteryRoiSensorDescription, ...]] = (
    BatteryRoiSensorDescription(
        key=_KEY_BEST_SIZE,
        translation_key=_KEY_BEST_SIZE,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=_best_roi_capacity_kwh,
    ),
    BatteryRoiSensorDescription(
        key=_KEY_PAYBACK,
        translation_key=_KEY_PAYBACK,
        native_unit_of_measurement=UnitOfTime.YEARS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=_payback_years,
    ),
    BatteryRoiSensorDescription(
        key=_KEY_ANNUAL_SAVING,
        translation_key=_KEY_ANNUAL_SAVING,
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement=_CURRENCY_EUR,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=_annual_saving_eur,
    ),
    BatteryRoiSensorDescription(
        key=_KEY_BEST_CAPACITY,
        translation_key=_KEY_BEST_CAPACITY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=_best_npv_capacity_kwh,
    ),
    BatteryRoiSensorDescription(
        key=_KEY_CYCLES,
        translation_key=_KEY_CYCLES,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=_cycles_per_year,
    ),
    BatteryRoiSensorDescription(
        key=_KEY_SELF_CONSUMPTION,
        translation_key=_KEY_SELF_CONSUMPTION,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=_self_consumption_pct,
    ),
    BatteryRoiSensorDescription(
        key=_KEY_IMPORT_SAVED,
        translation_key=_KEY_IMPORT_SAVED,
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=1,
        value_fn=_import_saved_kwh,
    ),
    BatteryRoiSensorDescription(
        key=_KEY_EXPORT_SAVED,
        translation_key=_KEY_EXPORT_SAVED,
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=1,
        value_fn=_export_saved_kwh,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Battery ROI Analyzer sensors from a config entry.

    Args:
        hass: The Home Assistant instance.
        entry: The config entry providing the coordinator (stored in
            `entry.runtime_data` by `__init__.async_setup_entry`).
        async_add_entities: Callback to register the created entities.
    """
    coordinator: BatteryRoiCoordinator = entry.runtime_data
    async_add_entities(
        BatteryRoiSensor(coordinator, entry, description)
        for description in SENSOR_DESCRIPTIONS
    )


class BatteryRoiSensor(CoordinatorEntity[BatteryRoiCoordinator], SensorEntity):
    """A single Battery ROI Analyzer sensor backed by coordinator data.

    All sensors for a config entry share one `device_info` so they group
    under a single device in the HA device registry.
    """

    _attr_has_entity_name = True
    entity_description: BatteryRoiSensorDescription

    def __init__(
        self,
        coordinator: BatteryRoiCoordinator,
        entry: ConfigEntry,
        description: BatteryRoiSensorDescription,
    ) -> None:
        """Initialize the sensor.

        Args:
            coordinator: Shared coordinator providing `BatteryRoiData`.
            entry: The config entry this sensor belongs to.
            description: Static metadata (unit, device class, value
                extractor) for this sensor.
        """
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title or "Battery ROI Analyzer",
            manufacturer="Battery ROI Analyzer",
            model="Battery ROI Simulator",
            entry_type=None,
        )

    @property
    def native_value(self) -> float | None:
        """Return the sensor's current value, extracted from coordinator data.

        Returns:
            The value produced by `entity_description.value_fn`, or
            `None` when the coordinator has no data yet or the
            underlying scenario result is unavailable (e.g. no payback
            within the configured battery lifetime).
        """
        data = self.coordinator.data
        if data is None:
            return None
        return self.entity_description.value_fn(data)

    @property
    def extra_state_attributes(self) -> Mapping[str, Any]:
        """Return per-capacity breakdown + monthly data for dashboard charts.

        The ``best_size`` and ``best_capacity`` sensors expose the full
        ``by_capacity`` (financial + simulation metrics per battery size)
        and ``monthly_data`` (monthly aggregated energy flows for heatmap)
        from the coordinator's cached ``BatteryRoiData``.
        """
        data = self.coordinator.data
        if data is None or self.entity_description.key not in (
            _KEY_BEST_SIZE, _KEY_BEST_CAPACITY
        ):
            return {}

        attrs: dict[str, Any] = {}
        if data.by_capacity:
            attrs["by_capacity"] = data.by_capacity
        if data.monthly_data:
            attrs["monthly_data"] = data.monthly_data
        return attrs
