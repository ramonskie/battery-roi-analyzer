"""The Battery ROI Analyzer integration.

Simulates home battery return-on-investment using existing historical
energy data pulled via the Home Assistant Statistics API. Does not
control a real battery — simulation/analysis only.
"""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path
from typing import Final

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN
from .coordinator import BatteryRoiCoordinator

PLATFORMS: Final = ["sensor"]

_LOGGER = logging.getLogger(__name__)

# Frontend card dir under www/ — card is copied here at setup_entry
# so HA serves it at /local/battery_roi/battery-roi-card.js.
_CARD_WWW_DIR: Final = "battery_roi"
_CARD_WWW_FILENAME: Final = "battery-roi-card.js"
_CARD_REGISTERED: Final = f"{DOMAIN}_card_registered"

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
    """Register the `battery_roi.recalculate` service."""
    async def _handle_recalculate(call: ServiceCall) -> None:
        await _async_handle_recalculate(hass, call)

    hass.services.async_register(
        DOMAIN,
        SERVICE_RECALCULATE,
        _handle_recalculate,
        schema=cv.make_entity_service_schema({}),
    )
    return True


async def _async_register_frontend(hass: HomeAssistant) -> None:
    """Serve the Lovelace card via ``/local/battery_roi/battery-roi-card.js``.

    Copies the card JS from the integration package to ``www/battery_roi/``
    (HA serves ``www/`` at ``/local/``) and registers it as a frontend
    extra JS URL so Lovelace discovers the custom element.

    This is the fallback for non-HACS installs.  When the repo is
    installed via HACS (*) HACS itself copies the card to
    ``www/community/battery-roi-analyzer/`` and registers the Lovelace
    resource — in that case this function is still safe to call (the
    copy is idempotent and ``add_extra_js_url`` is a no-op when the URL
    is already registered).

    (*) The repo declares both ``integration`` and ``plugin`` categories
    in ``hacs.json``.
    """
    src = Path(__file__).parent / "frontend" / _CARD_WWW_FILENAME
    if not src.exists():
        _LOGGER.warning("Frontend card not found at %s", src)
        return

    www_dir = hass.config.path("www", _CARD_WWW_DIR)
    os.makedirs(www_dir, exist_ok=True)
    dst = os.path.join(www_dir, _CARD_WWW_FILENAME)
    try:
        shutil.copy2(str(src), dst)
    except OSError as err:
        _LOGGER.warning("Could not copy frontend card to %s: %s", dst, err)
        return

    url_path = f"/local/{_CARD_WWW_DIR}/{_CARD_WWW_FILENAME}"
    from homeassistant.components.frontend import add_extra_js_url  # noqa: PLC0415

    await add_extra_js_url(hass, url_path)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Battery ROI Analyzer from a config entry."""
    coordinator = BatteryRoiCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    # Register Lovelace card once per HA session.
    if not hass.data.get(_CARD_REGISTERED):
        await _async_register_frontend(hass)
        hass.data[_CARD_REGISTERED] = True

    return True


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

    # Clean up www/battery_roi/ card file copied at setup.
    www_dir = hass.config.path("www", _CARD_WWW_DIR)
    try:
        if Path(www_dir).is_dir():
            shutil.rmtree(www_dir)
    except OSError:
        _LOGGER.warning("Could not remove %s", www_dir)

    return unload_ok
