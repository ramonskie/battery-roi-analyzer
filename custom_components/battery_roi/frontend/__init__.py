"""Lovelace card registration for the Battery ROI Analyzer.

Registers ``battery-roi-card.js`` so users can add it as a custom card
in any Lovelace dashboard.

Strategy — three registration paths for maximum compatibility:
  1. ``async_register_static_paths`` — serves the JS file under URL_BASE
  2. ``lovelace.resources.async_create_item`` — registers as Lovelace
     resource (works in storage mode)
  3. ``frontend.add_extra_js_url`` — sync fallback that loads the JS on
     every HA frontend page (guaranteed to work in all HA versions)
"""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components import frontend as frontend_component
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from ..const import JSMODULES, URL_BASE

_LOGGER = logging.getLogger(__name__)


class JSModuleRegistration:
    """Registers frontend JavaScript modules for this integration.

    Thread-safe after ``async_register()`` completes.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        """Store reference to HA instance."""
        self.hass = hass

    async def async_register(self) -> None:
        """Run all three registration strategies."""
        # 1. Serve the frontend/ directory so the JS is fetchable
        await self._async_register_static_paths()

        # 2. Register as a Lovelace resource (storage mode only)
        await self._async_register_lovelace_resource()

        # 3. Sync fallback: add to every frontend page
        self._register_extra_js_url()

    # ------------------------------------------------------------------
    #  Static path
    # ------------------------------------------------------------------

    async def _async_register_static_paths(self) -> None:
        """Serve the frontend/ directory at URL_BASE.

        Idempotent — HA silently ignores duplicate registrations.
        """
        frontend_dir = Path(__file__).parent
        try:
            await self.hass.http.async_register_static_paths([
                StaticPathConfig(URL_BASE, str(frontend_dir), cache_headers=False),
            ])
            _LOGGER.debug("Static path: %s -> %s", URL_BASE, frontend_dir)
        except RuntimeError:
            _LOGGER.debug("Static path already registered: %s", URL_BASE)

    # ------------------------------------------------------------------
    #  Lovelace resource (storage mode only)
    # ------------------------------------------------------------------

    async def _async_register_lovelace_resource(self) -> None:
        """Register each JS module as a Lovelace resource.

        Only works when the dashboard is in storage mode (the default).
        In YAML mode the user must add the resource manually.
        """
        lovelace = self.hass.data.get("lovelace")
        if lovelace is None:
            _LOGGER.debug("Lovelace not available yet, skipping resource registration")
            return

        # Check mode
        mode = getattr(lovelace, "mode",
                       getattr(lovelace, "resource_mode", None))
        if mode != "storage":
            _LOGGER.debug("Lovelace mode is '%s', skipping auto-registration", mode)
            return

        resources = getattr(lovelace, "resources", None)
        if resources is None or not getattr(resources, "loaded", False):
            _LOGGER.debug("Lovelace resources not loaded, skipping")
            return

        for module in JSMODULES:
            url = f"{URL_BASE}/{module['filename']}"
            try:
                existing = next(
                    (r for r in resources.async_items() if r["url"] == url),
                    None,
                )
                if existing is not None:
                    _LOGGER.debug("Resource already exists: %s", url)
                    continue
                _LOGGER.info("Adding Lovelace resource: %s", url)
                await resources.async_create_item({
                    "res_type": "module",
                    "url": url,
                })
            except Exception as exc:  # noqa: BLE001
                _LOGGER.warning("Could not register Lovelace resource %s: %s", url, exc)

    # ------------------------------------------------------------------
    #  Sync fallback — add_extra_js_url
    # ------------------------------------------------------------------

    def _register_extra_js_url(self) -> None:
        """Register the card JS as a global frontend extra JS URL.

        ``add_extra_js_url`` is **synchronous** (no ``await``) and loads
        the script on every HA frontend page.  This is a reliable fallback
        that works regardless of Lovelace mode or storage/YAML config.
        """
        for module in JSMODULES:
            url = f"{URL_BASE}/{module['filename']}"
            try:
                frontend_component.add_extra_js_url(self.hass, url)
                _LOGGER.debug("Registered extra JS URL: %s", url)
            except Exception as exc:  # noqa: BLE001
                _LOGGER.warning("Could not register extra JS URL %s: %s", url, exc)
