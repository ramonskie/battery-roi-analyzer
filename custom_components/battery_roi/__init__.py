"""The Battery ROI Analyzer integration.

Simulates home battery return-on-investment using existing historical
energy data pulled via the Home Assistant Statistics API. Does not
control a real battery — simulation/analysis only.
"""

from __future__ import annotations

import logging
from typing import Final

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant, ServiceCall, CoreState
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import async_call_later

from .const import DOMAIN, URL_BASE
from .coordinator import BatteryRoiCoordinator
from .frontend import JSModuleRegistration

_LOGGER = logging.getLogger(__name__)

PLATFORMS: Final = ["sensor"]

# Force an immediate coordinator refresh, bypassing the daily simulation
# cache (`coordinator.SIMULATION_UPDATE_INTERVAL`). See `services.yaml`.
SERVICE_RECALCULATE: Final = "recalculate"


async def _async_handle_recalculate(hass: HomeAssistant, call: ServiceCall) -> None:
    """Handle the `battery_roi.recalculate` service call.

    Resolves the target entity ids back to config entries, then forces an
    immediate `async_refresh()` on each affected entry's coordinator.
    """
    entity_ids: list[str] = call.data.get(ATTR_ENTITY_ID, [])
    entity_registry = er.async_get(hass)

    entry_ids: set[str] = set()
    for entity_id in entity_ids:
        entity_entry = entity_registry.async_get(entity_id)
        if entity_entry is not None and entity_entry.config_entry_id is not None:
            entry_ids.add(entity_entry.config_entry_id)

    for entry_id in entry_ids:
        entry = hass.config_entries.async_get_entry(entry_id)
        if entry is None:
            continue
        coordinator: BatteryRoiCoordinator | None = getattr(entry, "runtime_data", None)
        if coordinator is None:
            continue
        await coordinator.async_refresh()


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up integration — register services + frontend resources."""
    await _register_services(hass)

    # Copy JS to www/ so it's served at /local/battery_roi/battery-roi-card.js.
    # Do this once at setup (not per entry).
    js_reg = JSModuleRegistration(hass)
    await js_reg.async_copy_to_www()

    # Register the Lovelace resource AFTER HA finishes starting up,
    # with retry until lovelace resources are loaded.
    async def _register_on_start() -> None:
        await _async_register_lovelace_resource(hass)

    if hass.state == CoreState.running:
        await _register_on_start()
    else:
        hass.bus.async_listen_once("homeassistant_started", lambda _: hass.async_create_task(_register_on_start()))

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Battery ROI Analyzer from a config entry."""
    coordinator = BatteryRoiCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


JS_RESOURCE_URL: Final = f"/local/{URL_BASE.strip('/')}/battery-roi-card.js"


async def _async_register_lovelace_resource(hass: HomeAssistant) -> None:
    """Register the card JS as a Lovelace resource (with retry).

    Lovelace resources are loaded via HA's module system which provides
    the import map for bare specifiers like ``"lit"``.  We retry until
    the ``lovelace`` data and its resources are available.
    """
    lovelace = hass.data.get("lovelace")
    if lovelace is None:
        _LOGGER.debug("Lovelace not ready, retrying in 5s")
        async_call_later(hass, 5, lambda _: hass.async_create_task(_async_register_lovelace_resource(hass)))
        return

    resources = getattr(lovelace, "resources", None)
    if resources is None:
        _LOGGER.debug("Lovelace resources not available, retrying in 5s")
        async_call_later(hass, 5, lambda _: hass.async_create_task(_async_register_lovelace_resource(hass)))
        return

    # In YAML mode, users manage resources manually
    mode = getattr(lovelace, "mode", None) or getattr(lovelace, "resource_mode", "storage")
    if mode != "storage":
        _LOGGER.debug("Lovelace in YAML mode — skipping automatic resource registration")
        return

    if not getattr(resources, "loaded", False):
        _LOGGER.debug("Lovelace resources not loaded yet, retrying in 5s")
        async_call_later(hass, 5, lambda _: hass.async_create_task(_async_register_lovelace_resource(hass)))
        return

    try:
        existing = list(resources.async_items())
        # Remove stale entries with different URLs
        for res in existing:
            url = res.get("url", "")
            if "battery-roi-card.js" in url and url != JS_RESOURCE_URL:
                await resources.async_delete_item(res["id"])
                _LOGGER.info("Removed stale resource: %s", url)

        # Create only if not already present
        if not any(
            r.get("url", "") == JS_RESOURCE_URL for r in resources.async_items()
        ):
            await resources.async_create_item({
                "res_type": "module",
                "url": JS_RESOURCE_URL,
            })
            _LOGGER.info("Registered Lovelace resource: %s", JS_RESOURCE_URL)
        else:
            _LOGGER.debug("Lovelace resource already registered: %s", JS_RESOURCE_URL)
    except Exception:  # noqa: BLE001
        _LOGGER.exception("Failed to register Lovelace resource")


async def _register_services(hass: HomeAssistant) -> None:
    """Register battery_roi services (idempotent, safe to call multiple times)."""
    if hass.services.has_service(DOMAIN, SERVICE_RECALCULATE):
        return

    async def _handle_recalculate(call: ServiceCall) -> None:
        await _async_handle_recalculate(hass, call)

    hass.services.async_register(
        DOMAIN,
        SERVICE_RECALCULATE,
        _handle_recalculate,
        schema=cv.make_entity_service_schema({}),
    )


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Re-run coordinator refresh when options are updated."""
    coordinator: BatteryRoiCoordinator = entry.runtime_data
    await coordinator.async_refresh()


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator: BatteryRoiCoordinator = entry.runtime_data
        await coordinator.async_shutdown()
        entry.runtime_data = None  # type: ignore[attr-defined]
    return unload_ok
