---
source: Official docs + GitHub raw source
library: home-assistant-core
package: homeassistant
topic: custom_component const.py conventions (DOMAIN, CONF_*, StrEnum)
fetched: 2026-07-15T00:00:00Z
official_docs: https://developers.home-assistant.io/docs/creating_component_code_review/
---

## DOMAIN constant

- Custom component's own `const.py` (in your integration folder, e.g. `custom_components/my_integration/const.py`) defines:
  ```python
  DOMAIN = "my_integration"
  ```
- No `Final` typing required by convention in most custom integrations, though core itself uses `Final` extensively (see below). Simple string, must match the folder name / manifest.json `domain` key.
- Used via `hass.data[DOMAIN]` for storing shared component/platform data (per code review checklist item 3.1).

## CONF_* constants (config entry / config flow keys)

- Reuse existing constants from `homeassistant.const` wherever possible — checklist explicitly says: "Use existing constants from const.py. Only add new constants to const.py if they are widely used. Otherwise keep them on component level."
- Naming pattern in HA core `homeassistant/const.py` (confirmed from live source):
  ```python
  CONF_HOST: Final = "host"
  CONF_PORT: Final = "port"
  CONF_API_KEY: Final = "api_key"
  CONF_USERNAME: Final = "username"
  CONF_PASSWORD: Final = "password"
  CONF_MODE: Final = "mode"
  CONF_SCAN_INTERVAL: Final = "scan_interval"
  ```
  Pattern: `CONF_<UPPER_SNAKE_CASE> : Final = "<lower_snake_case_value>"` — the constant name usually mirrors the string value exactly (uppercased).
- For integration-local, non-widely-shared keys, define them the same way in your own `const.py`:
  ```python
  CONF_API_URL: Final = "api_url"
  CONF_POLL_INTERVAL: Final = "poll_interval"
  ```
- Schema should use as many generic `CONF_*` keys from `homeassistant.const` as possible instead of inventing new ones (checklist item 2.3).

## StrEnum usage

Confirmed from live `homeassistant/const.py` (2026.8.0dev):
```python
from enum import StrEnum
```
- HA core has **fully migrated to Python's stdlib `enum.StrEnum`** (Python 3.11+ builtin). The old `homeassistant.backports.enum.StrEnum` shim is legacy/no longer imported in current core const.py — stdlib `StrEnum` is used directly.
- Used extensively for grouped/mode/category constants, e.g.:
  ```python
  class EntityCategory(StrEnum):
      """Category of an entity."""
      CONFIG = "config"
      DIAGNOSTIC = "diagnostic"

  class UnitOfTemperature(StrEnum):
      """Temperature units."""
      CELSIUS = "°C"
      FAHRENHEIT = "°F"
      KELVIN = "K"
  ```
- For a custom component's "scenario/mode" enum (e.g. operating modes, states), the current recommended pattern is:
  ```python
  from enum import StrEnum

  class MyIntegrationMode(StrEnum):
      """Operating modes for My Integration."""

      NORMAL = "normal"
      ECO = "eco"
      BOOST = "boost"
  ```
- Deprecated enum members use `DeprecatedConstantEnum` wrapper (only relevant to core, not typically needed in custom components).

## Example custom_component const.py pattern

```python
"""Constants for My Integration."""
from enum import StrEnum
from typing import Final

DOMAIN: Final = "my_integration"

# Config entry keys — reuse from homeassistant.const when possible:
# from homeassistant.const import CONF_HOST, CONF_PORT, CONF_USERNAME, CONF_PASSWORD
CONF_API_URL: Final = "api_url"
CONF_POLL_INTERVAL: Final = "poll_interval"
CONF_MODE: Final = "mode"  # (also exists in homeassistant.const as ATTR_MODE-adjacent; prefer core const if suitable)

DEFAULT_POLL_INTERVAL: Final = 60


class OperatingMode(StrEnum):
    """Operating modes exposed by My Integration."""

    NORMAL = "normal"
    ECO = "eco"
    BOOST = "boost"
```

## Notes

- `Final` typing (from `typing`) is standard in core const.py for scalar constants; optional but good practice in custom components.
- Docstring `"""Constants for X."""` at top of file is HA style-guideline convention.
- Prefer importing shared `CONF_*`/`ATTR_*`/`STATE_*` from `homeassistant.const` over redefining — only define new ones locally when integration-specific.
