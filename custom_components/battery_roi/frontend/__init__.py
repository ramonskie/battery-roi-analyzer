"""Lovelace card registration for the Battery ROI Analyzer.

Registers ``battery-roi-card.js`` so users can add it as a custom card
in any Lovelace dashboard.

Strategy — three safe paths (no ``async_register_static_paths`` — that
can corrupt HA's HTTP routing table when called early):

  1. Copy to ``www/battery_roi/`` — served by HA's built-in ``/local/``
     (always works from HA core, no custom routing needed)
  2. ``lovelace.resources.async_create_item`` — registers as Lovelace
     resource (works in storage mode)
  3. ``frontend.add_extra_js_url`` — sync fallback that loads the JS on
     every HA frontend page (guaranteed to work in all HA versions)
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from homeassistant.components import frontend as frontend_component
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
        """Run all three registration strategies (safe subset)."""
        await self._async_copy_to_www()
        await self._async_register_lovelace_resource()
        self._register_extra_js_url()

    # ------------------------------------------------------------------
    #  www/ copy — serve via HA's built-in /local/ (ALWAYS works)
    # ------------------------------------------------------------------

    async def _async_copy_to_www(self) -> None:
        """Copy JS files to ``www/battery_roi/``.

        HA always serves the ``www/`` directory at ``/local/``.  This is
        the most reliable way to serve custom card files — it works on
        every HA version without depending on any HTTP routing APIs.
        """
        www_dir = Path(self.hass.config.path("www", URL_BASE.strip("/")))

        try:
            www_dir.mkdir(parents=True, exist_ok=True)
        except Exception as exc:  # noqa: BLE001
            _LOGGER.warning("Cannot create www dir %s: %s", www_dir, exc)
            return

        src_dir = Path(__file__).parent
        for module in JSMODULES:
            src = src_dir / module["filename"]
            dst = www_dir / module["filename"]
            try:
                await self.hass.async_add_executor_job(shutil.copy2, str(src), str(dst))
                _LOGGER.debug("Copied %s -> %s", src, dst)
            except Exception as exc:  # noqa: BLE001
                _LOGGER.warning("Failed to copy %s to www: %s", src, exc)

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
            url = self._local_url(module["filename"])
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
        """Register /local/ URL as extra JS URL on every frontend page.

        ``add_extra_js_url`` is **synchronous** (no ``await``) — it adds
        the URL to the frontend's ``UrlManager``, which injects it as a
        ``<script type="module">`` into the index.html template on every
        request.  Uses only the ``/local/`` path from the www/ copy.
        """
        for module in JSMODULES:
            url = self._local_url(module["filename"])
            try:
                frontend_component.add_extra_js_url(self.hass, url)
                _LOGGER.debug("Registered extra JS URL: %s", url)
            except Exception as exc:  # noqa: BLE001
                _LOGGER.warning("Could not register extra JS URL %s: %s", url, exc)

    # ------------------------------------------------------------------
    #  URL helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _local_url(filename: str) -> str:
        """Return the /local/ URL for the JS file (from www/ copy)."""
        return f"/local/{URL_BASE.strip('/')}/{filename}"
