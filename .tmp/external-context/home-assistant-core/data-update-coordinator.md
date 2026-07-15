---
source: Context7 API
library: Home Assistant Developers Docs
package: home-assistant-core
topic: DataUpdateCoordinator pattern (coordinator.py)
fetched: 2026-07-15T00:00:00Z
official_docs: https://developers.home-assistant.io/docs/integration_fetching_data
---

## coordinator.py skeleton with `_async_setup` (HA 2024.8+)

```python
class MyUpdateCoordinator(DataUpdateCoordinator[MyDataType]):
    prereq_data: SomeData

    def __init__(self, hass: HomeAssistant) -> None:
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=SCAN_INTERVAL)
        self.my_api = MyApi()

    async def _async_setup(self) -> None:
        """One-time init, called automatically during first refresh."""
        self.prereq_data = await self.my_api.get_initial_data()

    async def _async_update_data(self) -> MyDataType:
        try:
            async with async_timeout.timeout(10):
                listening_idx = set(self.async_contexts())
                return await self.my_api.fetch_data(listening_idx)
        except ApiAuthError as err:
            # Cancels future updates, starts SOURCE_REAUTH config flow
            raise ConfigEntryAuthFailed from err
        except ApiError as err:
            raise UpdateFailed(f"Error communicating with API: {err}")
        except ApiRateLimited as err:
            raise UpdateFailed(retry_after=60)
```

Note: `asyncio.TimeoutError` and `aiohttp.ClientError` are already handled by the coordinator base class.
`_async_setup` gets same error handling as `_async_update_data` (handles `ConfigEntryError`/`ConfigEntryAuthFailed`).

## Wiring in `__init__.py` (async_setup_entry)

```python
async def async_setup_entry(hass, config_entry, async_add_entities):
    my_api = config_entry.runtime_data
    coordinator = MyCoordinator(hass, config_entry, my_api)

    # Raises ConfigEntryNotReady on failure -> HA retries setup later
    await coordinator.async_config_entry_first_refresh()

    async_add_entities(
        MyEntity(coordinator, idx) for idx, ent in enumerate(coordinator.data)
    )
```

Convention: put coordinator class in `coordinator.py`, shared entity base class in `entity.py` (quality-scale "common-modules" rule).
