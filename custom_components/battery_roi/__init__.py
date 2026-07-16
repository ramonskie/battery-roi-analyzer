"""The Battery ROI Analyzer integration.

Simulates home battery return-on-investment using existing historical
energy data pulled via the Home Assistant Statistics API. Does not
control a real battery — simulation/analysis only.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Final

from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import async_call_later

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS: Final = ["sensor"]

SERVICE_RECALCULATE: Final = "recalculate"

# URL where the Lovelace card JS is served (via StaticPathConfig below).
_CARD_JS_URL: Final = f"/{DOMAIN}/battery-roi-card.js"


async def _async_handle_recalculate(hass: HomeAssistant, call: ServiceCall) -> None:
    """Handle the `battery_roi.recalculate` service call."""
    entity_ids: list[str] = call.data.get(ATTR_ENTITY_ID, [])
    entity_registry_obj = er.async_get(hass)

    entry_ids: set[str] = set()
    for entity_id in entity_ids:
        entity_entry = entity_registry_obj.async_get(entity_id)
        if entity_entry is not None and entity_entry.config_entry_id is not None:
            entry_ids.add(entity_entry.config_entry_id)

    for entry_id in entry_ids:
        entry = hass.config_entries.async_get_entry(entry_id)
        if entry is None:
            continue
        coordinator = getattr(entry, "runtime_data", None)
        if coordinator is None:
            continue
        await coordinator.async_refresh()


# ── Frontend card registration (WebRTC / Browser Mod pattern) ──────────

async def _register_frontend(hass: HomeAssistant) -> None:
    """Serve the card JS and register it with the Lovelace frontend.

    Follows the same proven pattern used by WebRTC Camera, Browser Mod,
    and HACS itself:

    1.  Serve the JS file via ``StaticPathConfig`` at ``/<domain>/<file>.js``.
    2.  Inject it into every page with ``add_extra_js_url``.
    3.  Auto-register as a Lovelace resource so the card picker sees it.
    """
    card_path = Path(__file__).parent / "www" / "battery-roi-card.js"

    # 1 ── Serve the JS file ──────────────────────────────────────────
    await hass.http.async_register_static_paths([
        StaticPathConfig(_CARD_JS_URL, str(card_path), True),
    ])
    _LOGGER.info("Serving card JS at %s", _CARD_JS_URL)

    # 2 ── Inject into every HA page ───────────────────────────────────
    try:
        from homeassistant.components.frontend import add_extra_js_url
        add_extra_js_url(hass, _CARD_JS_URL, es5=False)
    except ImportError:
        _LOGGER.warning("add_extra_js_url not available — card only via resource")
    _LOGGER.info("add_extra_js_url: %s", _CARD_JS_URL)

    # 3 ── Auto-register as Lovelace resource ─────────────────────────
    # Retries until the Lovelace resources manager is ready, then
    # creates the resource (if missing) or cleans up stale entries.
    _schedule_lovelace_resource_setup(hass)


# ── Lovelace resource registration (retry loop) ─────────────────────────

_LOVELACE_SETUP_SCHEDULED = False


def _schedule_lovelace_resource_setup(hass: HomeAssistant) -> None:
    """Schedule the Lovelace resource registration retry loop."""
    global _LOVELACE_SETUP_SCHEDULED  # noqa: PLW0603
    if _LOVELACE_SETUP_SCHEDULED:
        return
    _LOVELACE_SETUP_SCHEDULED = True
    hass.async_create_task(_lovelace_resource_setup(hass))


async def _lovelace_resource_setup(hass: HomeAssistant) -> None:
    """Register the card JS as a Lovelace resource (with retry)."""
    lovelace = hass.data.get("lovelace")
    if lovelace is None:
        _LOGGER.debug("Lovelace not ready, retrying in 5s")
        async_call_later(hass, 5, lambda _: _schedule_lovelace_resource_setup(hass))
        return

    resources = getattr(lovelace, "resources", None)
    if resources is None:
        _LOGGER.debug("Lovelace resources object not available, retrying in 5s")
        async_call_later(hass, 5, lambda _: _schedule_lovelace_resource_setup(hass))
        return

    # YAML-mode users manage resources manually — skip auto-registration.
    mode = getattr(lovelace, "mode", None) or getattr(lovelace, "resource_mode", None)
    if mode not in (None, "storage"):
        _LOGGER.debug("Lovelace in YAML mode (%s) — skip auto-registration", mode)
        return

    if not getattr(resources, "loaded", False):
        _LOGGER.debug("Lovelace resources not loaded yet, retrying in 5s")
        async_call_later(hass, 5, lambda _: _schedule_lovelace_resource_setup(hass))
        return

    _LOGGER.debug("Lovelace resources ready — registering card resource")

    try:
        existing = resources.async_items()
        # Remove any stale entries for our card (wrong URL or broken type).
        for res in list(existing):
            url = res.get("url", "")
            if "battery-roi-card.js" not in url:
                continue
            stored_type = res.get("type") or res.get("res_type", "")
            if url != _CARD_JS_URL or stored_type != "module":
                _LOGGER.info(
                    "Removing broken/stale resource: %s (type=%r)", url, stored_type
                )
                await resources.async_delete_item(res["id"])

        # Create if not already present.
        current_urls = {r.get("url", "") for r in resources.async_items()}
        if _CARD_JS_URL not in current_urls:
            await resources.async_create_item({
                "res_type": "module",
                "url": _CARD_JS_URL,
            })
            _LOGGER.info("Registered Lovelace resource: %s", _CARD_JS_URL)
        else:
            _LOGGER.debug("Lovelace resource already registered: %s", _CARD_JS_URL)
    except Exception:  # noqa: BLE001
        _LOGGER.exception("Failed to register Lovelace resource")


# ── HA lifecycle ────────────────────────────────────────────────────────


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up integration — register services + frontend card.

    NOTE: In HA >=2026, ``async_setup`` runs on a SyncWorker thread.
    Work that touches ``hass.data['lovelace']`` happens in background
    tasks scheduled from here.
    """
    from .coordinator import BatteryRoiCoordinator  # noqa: F811

    await _register_services(hass)
    await _register_frontend(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Battery ROI Analyzer from a config entry."""
    from .coordinator import BatteryRoiCoordinator

    coordinator = BatteryRoiCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Re-run coordinator refresh when options are updated."""
    coordinator = entry.runtime_data
    await coordinator.async_refresh()


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator = entry.runtime_data
        await coordinator.async_shutdown()
        entry.runtime_data = None  # type: ignore[attr-defined]
    return unload_ok


async def _register_services(hass: HomeAssistant) -> None:
    """Register battery_roi services (idempotent)."""
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
