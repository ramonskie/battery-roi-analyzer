"""Repairs support for the Battery ROI Analyzer integration.

Defines a repair flow for the most common misconfiguration this
integration can hit at runtime: one of the configured energy sensors
(`import_sensor`/`export_sensor`/`production_sensor`/`consumption_sensor`)
becomes unavailable or has no recorder statistics history. When this
happens, `coordinator.BatteryRoiCoordinator._async_update_data` raises
`UpdateFailed` (see `coordinator.py`'s `KeyError`/`ValueError` handling
around missing sensor configuration and "no historical statistics
available yet"). That failure alone only marks entities unavailable; to
surface an actionable, user-guided fix in Settings > Repairs, the
coordinator (or `__init__.py`) should additionally call
`async_create_missing_sensor_issue` for the specific sensor key at the
point of failure, e.g.:

    from .repairs import async_create_missing_sensor_issue
    ...
    except KeyError as err:
        await async_create_missing_sensor_issue(hass, entry, sensor_key=...)
        raise UpdateFailed(...) from err

This module only defines the issue helper + the `RepairsFlow` itself;
wiring the `async_create_issue` call into the coordinator's error paths
is intentionally left out of this file's scope (tracked separately) so
this subtask stays limited to `repairs.py`.
"""

from __future__ import annotations

from typing import Any, Final

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.selector import EntitySelector, EntitySelectorConfig

from .const import DOMAIN

# Issue id prefix for "a configured sensor is missing/invalid" repairs.
# The full issue id is f"{_ISSUE_MISSING_SENSOR}_{entry_id}_{sensor_key}"
# so each config entry + sensor field gets its own dismissible issue.
_ISSUE_MISSING_SENSOR: Final = "missing_sensor"

# `sensor_key` values this module knows how to build a fix-flow step for.
# Mirrors the CONF_* sensor keys from `const.py`.
VALID_SENSOR_KEYS: Final = (
    "import_sensor",
    "export_sensor",
    "production_sensor",
    "consumption_sensor",
)


def _issue_id(entry_id: str, sensor_key: str) -> str:
    """Build the deterministic issue id for a missing-sensor repair.

    Args:
        entry_id: The config entry id the issue belongs to.
        sensor_key: Which `CONF_*_SENSOR` field is affected.

    Returns:
        A stable issue id, unique per config entry + sensor field.
    """
    return f"{_ISSUE_MISSING_SENSOR}_{entry_id}_{sensor_key}"


async def async_create_missing_sensor_issue(
    hass: HomeAssistant, entry: ConfigEntry, *, sensor_key: str
) -> None:
    """Create (or update) a repair issue for a missing/invalid sensor.

    Intended to be called from `coordinator.BatteryRoiCoordinator`'s
    `_async_update_data` error handling whenever a specific configured
    sensor is the identified cause of a failed refresh (missing entity,
    or no statistics history yet).

    Args:
        hass: The Home Assistant instance.
        entry: The config entry the affected sensor belongs to.
        sensor_key: Which `CONF_*_SENSOR` field is affected (must be one
            of `VALID_SENSOR_KEYS`).
    """
    ir.async_create_issue(
        hass,
        DOMAIN,
        _issue_id(entry.entry_id, sensor_key),
        is_fixable=True,
        is_persistent=False,
        severity=ir.IssueSeverity.ERROR,
        translation_key="missing_sensor",
        translation_placeholders={"sensor_key": sensor_key},
        data={"entry_id": entry.entry_id, "sensor_key": sensor_key},
    )


def async_delete_missing_sensor_issue(
    hass: HomeAssistant, entry: ConfigEntry, *, sensor_key: str
) -> None:
    """Clear a previously-created missing-sensor issue once resolved.

    Intended to be called after a successful coordinator refresh, once
    the previously-failing sensor is valid again.

    Args:
        hass: The Home Assistant instance.
        entry: The config entry the affected sensor belongs to.
        sensor_key: Which `CONF_*_SENSOR` field to clear the issue for.
    """
    ir.async_delete_issue(hass, DOMAIN, _issue_id(entry.entry_id, sensor_key))


class MissingSensorRepairFlow(ir.RepairsFlow):
    """Guided fix flow: let the user re-select the affected sensor.

    On confirmation, updates the config entry's `options` with the newly
    selected entity id for `sensor_key`. Saving options triggers
    `BatteryRoiCoordinator`'s `add_update_listener` callback, which
    immediately re-runs the simulation with the corrected sensor.
    """

    def __init__(self, entry_id: str, sensor_key: str) -> None:
        """Initialize the flow with the affected entry/sensor field.

        Args:
            entry_id: The config entry id this repair applies to.
            sensor_key: Which `CONF_*_SENSOR` field needs re-selection.
        """
        self._entry_id = entry_id
        self._sensor_key = sensor_key

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """First (and only) step: confirm before showing the selector."""
        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Prompt the user to re-select the affected sensor entity.

        Args:
            user_input: The submitted form data, containing the newly
                selected `sensor_key` entity id, or `None` on first
                display.

        Returns:
            A `FlowResult` — either the re-shown form (with errors) or
            `async_create_entry` once the sensor is updated and the
            issue is resolved.
        """
        errors: dict[str, str] = {}
        if user_input is not None:
            entry = self.hass.config_entries.async_get_entry(self._entry_id)
            if entry is None:
                return self.async_abort(reason="entry_not_found")

            new_entity_id = user_input[self._sensor_key]
            state = self.hass.states.get(new_entity_id)
            if state is None:
                errors[self._sensor_key] = "invalid_sensor"
            else:
                self.hass.config_entries.async_update_entry(
                    entry,
                    options={**entry.options, self._sensor_key: new_entity_id},
                )
                async_delete_missing_sensor_issue(
                    self.hass, entry, sensor_key=self._sensor_key
                )
                return self.async_create_entry(data={})

        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(self._sensor_key): EntitySelector(
                        EntitySelectorConfig(domain="sensor")
                    ),
                }
            ),
            description_placeholders={"sensor_key": self._sensor_key},
            errors=errors,
        )


async def async_create_fix_flow(
    hass: HomeAssistant,
    issue_id: str,
    data: dict[str, Any] | None,
) -> ir.RepairsFlow:
    """Create the repair flow for a given issue id.

    Required entry point looked up by Home Assistant's repairs frontend
    (`homeassistant.components.repairs`) via `<domain>.repairs`.

    Args:
        hass: The Home Assistant instance.
        issue_id: The id of the issue being fixed.
        data: The `data` dict the issue was created with (contains
            `entry_id` and `sensor_key` for missing-sensor issues).

    Returns:
        A `MissingSensorRepairFlow` instance for known missing-sensor
        issues.

    Raises:
        ValueError: If `issue_id`/`data` don't correspond to a known,
            fixable issue type.
    """
    if data is not None and issue_id.startswith(f"{_ISSUE_MISSING_SENSOR}_"):
        entry_id = data["entry_id"]
        sensor_key = data["sensor_key"]
        return MissingSensorRepairFlow(entry_id, sensor_key)

    raise ValueError(f"Unknown repair issue_id: {issue_id}")
