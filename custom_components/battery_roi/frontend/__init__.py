"""Lovelace card resource registration for the Battery ROI Analyzer.

Provides :class:`JSModuleRegistration` which registers the
``battery-roi-card.js`` frontend module as a Lovelace resource so users
can add the card to their dashboard without manual URL configuration.

Uses the current HA APIs:
  * ``hass.http.async_register_static_paths`` to serve the JS file
  * ``lovelace.resources.async_create_item`` to register the Lovelace
    resource (storage mode only)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_call_later

from ..const import JSMODULES, URL_BASE

_LOGGER = logging.getLogger(__name__)


class JSModuleRegistration:
    """Registers JavaScript modules in Home Assistant.

    Call ``async_register()`` from the integration's ``__init__.py``
    after ``EVENT_HOMEASSISTANT_STARTED`` fires, to guarantee Lovelace
    resources are available.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        """Store reference to HA instance."""
        self.hass = hass
        self.lovelace = self.hass.data.get("lovelace")

    async def async_register(self) -> None:
        """Register all frontend resources (static path + Lovelace items)."""
        await self._async_register_static_paths()

        if self._lovelace_is_storage_mode():
            await self._async_wait_for_lovelace_resources()

    # ------------------------------------------------------------------
    #  Static path
    # ------------------------------------------------------------------

    async def _async_register_static_paths(self) -> None:
        """Serve the frontend/ directory under URL_BASE.

        Idempotent — HA silently ignores duplicate path registrations.
        """
        frontend_dir = Path(__file__).parent
        try:
            await self.hass.http.async_register_static_paths([
                StaticPathConfig(URL_BASE, str(frontend_dir), cache_headers=False),
            ])
            _LOGGER.debug("Static path registered: %s -> %s", URL_BASE, frontend_dir)
        except RuntimeError:
            _LOGGER.debug("Static path already registered: %s", URL_BASE)

    # ------------------------------------------------------------------
    #  Lovelace resource
    # ------------------------------------------------------------------

    def _lovelace_is_storage_mode(self) -> bool:
        """Return True when Lovelace is in storage (not YAML) mode."""
        if self.lovelace is None:
            return False
        # Different HA versions expose mode differently
        mode = getattr(self.lovelace, "mode",
                       getattr(self.lovelace, "resource_mode", "yaml"))
        return mode == "storage"

    async def _async_wait_for_lovelace_resources(self) -> None:
        """Poll until Lovelace resources are loaded, then register."""

        async def _check_loaded(_now: Any) -> None:
            if self.lovelace.resources.loaded:
                await self._async_register_modules()
            else:
                _LOGGER.debug("Lovelace resources not loaded yet, retrying in 5s")
                async_call_later(self.hass, 5, _check_loaded)

        await _check_loaded(0)

    async def _async_register_modules(self) -> None:
        """Register each JS module as a Lovelace resource (if missing)."""
        for module in JSMODULES:
            url = f"{URL_BASE}/{module['filename']}"
            existing = next(
                (r for r in self.lovelace.resources.async_items() if r["url"] == url),
                None,
            )
            if existing is not None:
                _LOGGER.debug("Resource already exists: %s", url)
                continue

            _LOGGER.info("Adding Lovelace resource: %s", url)
            await self.lovelace.resources.async_create_item({
                "res_type": "module",
                "url": url,
            })
