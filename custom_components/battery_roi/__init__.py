"""The Battery ROI Analyzer integration.

Simulates home battery return-on-investment using existing historical
energy data pulled via the Home Assistant Statistics API. Does not
control a real battery — simulation/analysis only.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Final

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID, EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import CoreState, HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN, JSMODULES, URL_BASE
from .coordinator import BatteryRoiCoordinator
from .frontend import JSModuleRegistration

PLATFORMS: Final = ["sensor"]

_LOGGER = logging.getLogger(__name__)

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
    """Register service, copy www/ files, register card in frontend."""
    # ── recalculate service ─────────────────────────────────────────
    async def _handle_recalculate(call: ServiceCall) -> None:
        await _async_handle_recalculate(hass, call)

    hass.services.async_register(
        DOMAIN,
        SERVICE_RECALCULATE,
        _handle_recalculate,
        schema=cv.make_entity_service_schema({}),
    )

    # ── www/ copy (safe file operation) ────────────────────────────
    js_reg = JSModuleRegistration(hass)
    await js_reg.async_copy_to_www()

    # ── Manage Lovelace resource ──────────────────────────────────
    # Replace stale /battery_roi/battery-roi-card.js resource with
    # correct /local/battery_roi/battery-roi-card.js.
    # A background task retries until Lovelace resources are loaded.
    async def _manage_resources() -> None:
        for attempt in range(12):  # up to ~60 s
            await asyncio.sleep(5)
            try:
                lovelace = hass.data.get("lovelace")
                if lovelace is None:
                    continue
                res = getattr(lovelace, "resources", None)
                if res is None or not getattr(res, "loaded", False):
                    continue

                for module in JSMODULES:
                    old_url = f"{URL_BASE}/{module['filename']}"
                    new_url = f"/local/{URL_BASE.strip('/')}/{module['filename']}"

                    # Delete stale resource
                    stale = next(
                        (r for r in res.async_items() if r["url"] == old_url),
                        None,
                    )
                    if stale is not None:
                        _LOGGER.info("Removing stale Lovelace resource: %s", old_url)
                        await res.async_delete_item(stale["id"])

                    # Add new resource if not already present
                    existing = next(
                        (r for r in res.async_items() if r["url"] == new_url),
                        None,
                    )
                    if existing is None:
                        _LOGGER.info("Adding Lovelace resource: %s", new_url)
                        await res.async_create_item({
                            "res_type": "module",
                            "url": new_url,
                        })
                return  # success
            except Exception:  # noqa: BLE001
                pass
        _LOGGER.warning("Could not manage Lovelace resources after 60 s")

    async def _on_started(_event=None) -> None:
        asyncio.create_task(_manage_resources())

    if hass.state == CoreState.running:
        asyncio.create_task(_manage_resources())
    else:
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _on_started)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Battery ROI Analyzer from a config entry."""
    coordinator = BatteryRoiCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    # Also trigger resource management from here (post-startup addition)
    js_reg = JSModuleRegistration(hass)
    asyncio.create_task(_manage_lovelace_resources_once(hass))

    return True


async def _manage_lovelace_resources_once(hass: HomeAssistant) -> None:
    """One-shot Lovelace resource management (for async_setup_entry)."""
    try:
        lovelace = hass.data.get("lovelace")
        if lovelace is None:
            return
        res = getattr(lovelace, "resources", None)
        if res is None or not getattr(res, "loaded", False):
            return
        for module in JSMODULES:
            old_url = f"{URL_BASE}/{module['filename']}"
            new_url = f"/local/{URL_BASE.strip('/')}/{module['filename']}"
            stale = next(
                (r for r in res.async_items() if r["url"] == old_url), None
            )
            if stale is not None:
                _LOGGER.info("Removing stale Lovelace resource: %s", old_url)
                await res.async_delete_item(stale["id"])
            existing = next(
                (r for r in res.async_items() if r["url"] == new_url), None
            )
            if existing is None:
                _LOGGER.info("Adding Lovelace resource: %s", new_url)
                await res.async_create_item({
                    "res_type": "module",
                    "url": new_url,
                })
    except Exception:  # noqa: BLE001
        pass


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
