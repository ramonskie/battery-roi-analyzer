---
source: Context7 API
library: Home Assistant Developers Docs
package: home-assistant-core
topic: repairs.py, issue registry, RepairsFlow
fetched: 2026-07-15T00:00:00Z
official_docs: https://developers.home-assistant.io/docs/core/platform/repairs
---

## Create a repair issue (issue registry)

```python
from homeassistant.helpers import issue_registry as ir

ir.async_create_issue(
    hass,
    DOMAIN,
    "manual_migration",
    breaks_in_ha_version="2022.9.0",
    is_fixable=False,
    severity=ir.IssueSeverity.ERROR,
    translation_key="manual_migration",
)
```

Non-fixable issue + halt setup example:

```python
async def async_setup_entry(hass: HomeAssistant, entry: MyConfigEntry) -> None:
    client = MyClient(entry.data[CONF_HOST])
    version = await client.get_version()
    if version < MINIMUM_VERSION:
        ir.async_create_issue(
            hass,
            DOMAIN,
            "outdated_version",
            is_fixable=False,
            issue_domain=DOMAIN,
            severity=ir.IssueSeverity.ERROR,
            translation_key="outdated_version",
        )
        raise ConfigEntryError(
            "Version of MyService is %s, which is lower than minimum version %s",
            version, MINIMUM_VERSION,
        )
```

## repairs.py — automatic RepairsFlow

```python
from __future__ import annotations
import voluptuous as vol
from homeassistant import data_entry_flow
from homeassistant.components.repairs import ConfirmRepairFlow, RepairsFlow
from homeassistant.core import HomeAssistant

class Issue1RepairFlow(RepairsFlow):
    async def async_step_init(
        self, user_input: dict[str, str] | None = None
    ) -> data_entry_flow.FlowResult:
        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict[str, str] | None = None
    ) -> data_entry_flow.FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data={})
        return self.async_show_form(step_id="confirm", data_schema=vol.Schema({}))

async def async_create_fix_flow(
    hass: HomeAssistant,
    issue_id: str,
    data: dict[str, str | int | float | None] | None,
) -> RepairsFlow:
    if issue_id == "issue_1":
        return Issue1RepairFlow()
```

Notes:
- Only raise repair issues for problems the user can act on (fixable via flow or informational instruction) — not generic "something is wrong" notices.
- `ConfirmRepairFlow` available for simple confirm-only repairs (no custom subclass needed).
