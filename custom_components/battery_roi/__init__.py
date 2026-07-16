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
from homeassistant.core import HomeAssistant, ServiceCall
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


# Track whether we've started the Lovelace resource registration.
# Prevents duplicate retry loops when there are multiple config entries.
_LOVELACE_REGISTRATION_STARTED = False


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up integration — register services + frontend resources.

    NOTE: In HA >=2026, this coroutine runs on a SyncWorker thread, NOT the
    event loop.  Do NOT call hass.async_create_task / async_listen_once here.
    Any work that touches ``hass.data['lovelace']`` must happen in
    ``async_setup_entry`` (which runs on the event loop).
    """
    await _register_services(hass)

    # Copy JS to www/ so it's served at /local/battery_roi/battery-roi-card.js.
    # Done once at setup, not per entry.
    js_reg = JSModuleRegistration(hass)
    await js_reg.async_copy_to_www()

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Battery ROI Analyzer from a config entry."""
    coordinator = BatteryRoiCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    # Start the Lovelace resource registration retry loop (runs on event
    # loop, safe to use async_call_later / async_create_task).
    global _LOVELACE_REGISTRATION_STARTED  # noqa: PLW0603
    if not _LOVELACE_REGISTRATION_STARTED:
        _LOVELACE_REGISTRATION_STARTED = True
        _LOGGER.debug("Starting Lovelace resource registration retry loop")
        _schedule_register_lovelace(hass)

    return True


JS_RESOURCE_URL: Final = f"/local/{URL_BASE.strip('/')}/battery-roi-card.js"


def _schedule_register_lovelace(hass: HomeAssistant) -> None:
    """Schedule _do_register_lovelace as a background task.

    Called from the event loop (``async_setup_entry`` or
    ``async_call_later``) so it's safe to use ``async_create_task``.
    """
    hass.async_create_task(_do_register_lovelace(hass))


async def _do_register_lovelace(hass: HomeAssistant) -> None:
    """Register the card JS as a Lovelace resource (with retry).

    Runs on the event loop.  Retries via ``async_call_later`` until the
    Lovelace resources manager is available and ``loaded``.
    """
    lovelace = hass.data.get("lovelace")
    if lovelace is None:
        _LOGGER.debug("Lovelace not ready, retrying in 5s")
        async_call_later(hass, 5, lambda _: _schedule_register_lovelace(hass))
        return

    resources = getattr(lovelace, "resources", None)
    if resources is None:
        _LOGGER.debug("Lovelace resources object not available, retrying in 5s")
        async_call_later(hass, 5, lambda _: _schedule_register_lovelace(hass))
        return

    # In YAML mode users manage resources manually
    mode = getattr(lovelace, "mode", None) or getattr(lovelace, "resource_mode", None)
    if mode not in (None, "storage"):
        _LOGGER.debug("Lovelace in YAML mode (%s) — skip auto-registration", mode)
        return

    if not getattr(resources, "loaded", False):
        _LOGGER.debug("Lovelace resources not loaded yet, retrying in 5s")
        async_call_later(hass, 5, lambda _: _schedule_register_lovelace(hass))
        return

    # ── resources are ready, register ──────────────────────────────
    _LOGGER.debug("Lovelace resources ready — registering card resource")

    try:
        existing = resources.async_items()
        # Remove stale entries: wrong URL, or right URL but broken type
        for res in list(existing):
            url = res.get("url", "")
            if "battery-roi-card.js" not in url:
                continue
            res_type = res.get("type") or res.get("res_type", "")
            if url != JS_RESOURCE_URL or res_type != "module":
                _LOGGER.info(
                    "Removing broken/stale resource: %s (type=%r)", url, res_type
                )
                await resources.async_delete_item(res["id"])

        # Create only if not already present (with correct URL + correct type)
        current_urls = {r.get("url", "") for r in resources.async_items()}
        if JS_RESOURCE_URL not in current_urls:
            await resources.async_create_item({
                "type": "module",
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
