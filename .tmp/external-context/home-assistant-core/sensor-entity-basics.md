---
source: Context7 API
library: Home Assistant Developers Docs
package: home-assistant-core
topic: SensorEntity, unique_id, device_info
fetched: 2026-07-15T00:00:00Z
official_docs: https://developers.home-assistant.io/docs/core/entity/sensor
---

## unique_id

```python
class MySensor(SensorEntity):
    def __init__(self, device_id: str) -> None:
        self._attr_unique_id = f"{device_id}_temperature"
```

## device_info (links entity to a device in the device registry)

```python
class MySensor(SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, device: MyDevice) -> None:
        self._attr_device_info = DeviceInfo(
            connections={(CONNECTION_NETWORK_MAC, device.mac)},
            name=device.name,
            serial_number=device.serial,
            hw_version=device.rev,
            sw_version=device.version,
            manufacturer="My Company",
            model="My Sensor",
            model_id="ABC-123",
            via_device=(DOMAIN, device.hub_id),
        )
```

## state_class (enables long-term statistics)

```python
@property
def state_class(self):
    return "measurement"  # or use _attr_state_class = SensorStateClass.MEASUREMENT
```

- `SensorStateClass.MEASUREMENT` — instantaneous values (temp, power).
- `SensorStateClass.TOTAL` / `TOTAL_INCREASING` — accumulating totals (energy, monetary savings).

## Entity naming

Set `_attr_has_entity_name = True` + `_attr_translation_key` for localized entity names
(see translations.md); device name + entity name are then combined automatically in the UI.
