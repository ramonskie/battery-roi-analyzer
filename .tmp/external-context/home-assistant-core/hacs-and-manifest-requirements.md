---
source: Context7 API
library: HACS documentation + Home Assistant Developers Docs
package: home-assistant-core
topic: hacs.json, manifest.json required fields, HACS repo folder structure
fetched: 2026-07-15T00:00:00Z
official_docs: https://hacs.xyz/docs/publish/start , https://developers.home-assistant.io/docs/creating_integration_manifest
---

## hacs.json (repo root, required for all HACS-published repos)

```json
{
  "name": "My Awesome Integration",
  "content_in_root": false,
  "zip_release": false,
  "filename": "my_awesome_card.js",
  "hide_default_branch": false,
  "country": ["US", "CA", "GB"],
  "homeassistant": "2024.4.0",
  "hacs": "1.34.0",
  "persistent_directory": "data"
}
```

Integration-specific minimal example:

```json
{
  "name": "My awesome thing",
  "country": "NO",
  "homeassistant": "0.99.9",
  "persistent_directory": "userfiles"
}
```

Key fields:
- `name` — display title in HACS UI.
- `content_in_root` — true if integration files live at repo root (no `custom_components/` wrapper) — normally **false** for integrations.
- `homeassistant` — minimum required HA core version.
- `hacs` — minimum required HACS version.
- `persistent_directory` — directory HACS preserves across upgrades (e.g. cached data/userfiles).
- `country` — restrict visibility to specific countries (optional).

## manifest.json (inside `custom_components/<domain>/`)

Minimum required keys: `domain`, `name`.

```json
{
  "domain": "my_integration",
  "name": "My Integration",
  "codeowners": ["@me"]
}
```

Common additional required/expected fields for a full custom integration:
- `codeowners` — list of GitHub usernames/teams responsible for the integration.
- `requirements` — pinned PyPI package versions (e.g. `"requirements": ["mylib==1.2.3"]`); must be hosted on PyPI, not GitHub.
- `config_flow` — `true` if integration is configured via UI (config_flow.py present).
- `iot_class` — one of `assumed_state`, `cloud_polling`, `cloud_push`, `local_polling`, `local_push`, `calculated`.
- `version` — required for custom (non-core) integrations distributed via HACS.
- `documentation`, `issue_tracker` — URLs.

## Repository folder structure (standard custom integration layout)

```
my_integration/                  (repo root)
├── hacs.json
├── README.md
├── info.md                      (optional, shown in HACS UI)
└── custom_components/
    └── my_integration/
        ├── __init__.py
        ├── manifest.json
        ├── config_flow.py
        ├── coordinator.py
        ├── entity.py
        ├── sensor.py
        ├── diagnostics.py
        ├── repairs.py
        ├── strings.json
        └── translations/
            └── en.json
```

`content_in_root: false` (default expectation) means HACS looks for the integration under
`custom_components/<domain>/` rather than at repo root.
