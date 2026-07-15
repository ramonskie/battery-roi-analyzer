---
source: Context7 API
library: Home Assistant Developers Docs
package: home-assistant-core
topic: diagnostics.py, async_get_config_entry_diagnostics, redaction
fetched: 2026-07-15T00:00:00Z
official_docs: https://developers.home-assistant.io/docs/core/integration/diagnostics
---

## diagnostics.py pattern

```python
from homeassistant.components.diagnostics import async_redact_data

TO_REDACT = [
    CONF_API_KEY,
    CONF_LATITUDE,
    CONF_LONGITUDE,
]

async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: MyConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    return {
        "entry_data": async_redact_data(entry.data, TO_REDACT),
        "data": entry.runtime_data.data,
    }
```

## Device diagnostics (optional)

```python
async def async_get_device_diagnostics(
    hass: HomeAssistant, entry: MyConfigEntry, device: DeviceEntry
) -> dict[str, Any]:
    appliance = _get_appliance_by_device_id(hass, device.id)
    return {
        "details": async_redact_data(appliance.raw_data, TO_REDACT),
        "data": appliance.data,
    }
```

## Testing (snapshot)

```python
async def test_diagnostics(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    init_integration: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    assert (
        await get_diagnostics_for_config_entry(hass, hass_client, init_integration)
        == snapshot
    )
```

**Rule**: never expose passwords, API keys/tokens, geo-coordinates, or PII — always redact via `async_redact_data(data, TO_REDACT)` before returning.
