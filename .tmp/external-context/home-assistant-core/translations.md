---
source: Context7 API
library: Home Assistant Developers Docs
package: home-assistant-core
topic: strings.json + translations/*.json for config flow and entity names
fetched: 2026-07-15T00:00:00Z
official_docs: https://developers.home-assistant.io/docs/internationalization/core
---

## strings.json top-level categories

`title`, `common`, `config`, `device`, `device_automation`, `entity`, `entity_component`,
`exceptions`, `issues` (repairs), `options`, `selectors`, `services`.

## Config/Options/Subentry flow translation shape

```json
{
  "config": {
    "flow_title": "Discovered Device ({host})",
    "entry_type": "Label explaining what an entry represents",
    "initiate_flow": {
      "reconfigure": "Menu/button label for reconfigure flow",
      "user": "Menu/button label for user flow"
    },
    "step": {
      "init": {
        "title": "Title of the `init` step.",
        "description": "Markdown shown with the step.",
        "data": { "api_key": "Label for the `api_key` field" },
        "sections": { "auth_options": { "name": "Label for `auth_options` section" } }
      }
    },
    "error": { "invalid_api_key": "Shown if `invalid_api_key` returned as error." },
    "abort": { "stale_api_key": "Shown if `stale_api_key` returned as abort reason. Supports Markdown." },
    "progress": { "slow_task": "Shown if `slow_task` returned as progress_action for async_show_progress." },
    "create_entry": {
      "default": "Shown in success dialog if async_create_entry(description=None).",
      "custom": "Shown if async_create_entry(description='custom')."
    }
  },
  "options": { "...": "same shape as config" },
  "config_subentries": {
    "subentry_type_1": { "...": "same shape as config, keyed by subentry type" }
  }
}
```

## Entity name translation

Requires `_attr_has_entity_name = True` + `_attr_translation_key`:

```python
class MySensor(SensorEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "phase_voltage"

    def __init__(self, device_id: str) -> None:
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)}, name="My device",
        )
```

```json
{
  "entity": {
    "sensor": {
      "phase_voltage": { "name": "Phase voltage" }
    }
  }
}
```

## Dev workflow

`strings.json` lives in integration root; `translations/en.json` etc. are auto-generated/uploaded via Lokalise — do not hand-edit non-English translation files. Iterate locally with:

```bash
python3 -m script.translations develop
```
