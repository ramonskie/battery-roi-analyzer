"""Lovelace card registration for the Battery ROI Analyzer.

Copies ``battery-roi-card.js`` to ``www/battery_roi/`` (served at
``/local/battery_roi/battery-roi-card.js``) and registers it via
``add_extra_js_url`` so the card appears in the Lovelace picker.

**Why not Lovelace resources?**  ``lovelace.resources.async_create_item``
leaves stale entries in ``.storage/lovelace_resources`` when the serving
URL changes — those stale entries 404 and cause ``load_resource.ts``
errors.  ``add_extra_js_url`` is the reliable mechanism: it injects a
``<script type="module">`` on every frontend page, which makes the
custom element definition and ``window.customCards.push()`` run
regardless of Lovelace's resource list.

**Timing**: ``add_extra_js_url`` must be called **after** the frontend
component's ``UrlManager`` is initialized (otherwise the URL is
registered on a throw-away manager that gets overwritten).  The call
is therefore made from ``async_setup_entry`` — not from
``EVENT_HOMEASSISTANT_STARTED`` which fires too early.
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
    """Registers frontend JavaScript modules for this integration."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass

    async def async_copy_to_www(self) -> None:
        """Copy JS files to ``www/battery_roi/``.

        HA always serves the ``www/`` directory at ``/local/``.  This
        works on every HA version without depending on any HTTP routing
        APIs.
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

    def register_extra_js_url(self) -> None:
        """Register /local/ URL as extra JS URL on every frontend page.

        ``add_extra_js_url`` injects a ``<script type="module">`` tag
        into the frontend HTML on every request.  Must be called **after**
        the frontend component's ``UrlManager`` is initialized.
        """
        for module in JSMODULES:
            url = f"/local/{URL_BASE.strip('/')}/{module['filename']}"
            try:
                frontend_component.add_extra_js_url(self.hass, url)
                _LOGGER.debug("Registered extra JS URL: %s", url)
            except Exception as exc:  # noqa: BLE001
                _LOGGER.warning("Could not register extra JS URL %s: %s", url, exc)
