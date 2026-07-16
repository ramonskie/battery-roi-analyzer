"""Frontend support for the Battery ROI Analyzer.

Copies ``battery-roi-card.js`` to ``www/battery_roi/`` so it is
served at ``/local/battery_roi/battery-roi-card.js``.

Lovelace resource management (delete stale, add new) is handled
in ``__init__.py`` via a background task with retry, because
``hass.data["lovelace"].resources`` may not be loaded yet when
``EVENT_HOMEASSISTANT_STARTED`` fires.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from homeassistant.core import HomeAssistant

from ..const import JSMODULES, URL_BASE

_LOGGER = logging.getLogger(__name__)


class JSModuleRegistration:
    """Copies JS module files to HA's ``www/`` directory."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass

    async def async_copy_to_www(self) -> None:
        """Copy JS files to ``www/battery_roi/``.

        HA serves the ``www/`` directory at ``/local/``.  This works
        on every HA version without depending on HTTP routing APIs.
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
