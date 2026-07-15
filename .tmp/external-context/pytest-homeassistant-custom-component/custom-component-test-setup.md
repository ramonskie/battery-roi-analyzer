---
source: Context7 API (matthewflamm/pytest-homeassistant-custom-component)
library: pytest-homeassistant-custom-component
package: pytest-homeassistant-custom-component
topic: conftest fixtures, hass fixture, mock config entry, snapshot testing for custom_components integration
fetched: 2026-07-15T00:00:00Z
official_docs: https://github.com/MatthewFlamm/pytest-homeassistant-custom-component
---

## Required: `enable_custom_integrations` fixture (mandatory >= 2021.6.0b0)

Plugin-provided fixture that lets custom components under `custom_components/` be discovered by `hass`:

```python
@pytest.fixture
def enable_custom_integrations(hass: HomeAssistant) -> None:
    """Enable custom integrations defined in the test dir."""
    hass.data.pop(loader.DATA_CUSTOM_COMPONENTS)
```

### Canonical `tests/conftest.py` pattern — autouse activation

```python
import pytest

@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield
```
This makes every test in the suite automatically able to load your custom integration without per-test boilerplate.

## `hass` fixture

Provided by the plugin (via `pytest_homeassistant_custom_component.plugins`) — gives a running `HomeAssistant` core instance for the test. Standard usage:
```python
async def test_something(hass: HomeAssistant, enable_custom_integrations):
    ...
```

## Mock Config Entry

Import from the plugin's `common` module (NOT `tests.common`):
```python
from pytest_homeassistant_custom_component.common import MockConfigEntry

async def test_setup_entry(hass):
    entry = MockConfigEntry(domain="my_integration", data={...})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
```

## Snapshot testing (syrupy integration)

```python
from pytest_homeassistant_custom_component.syrupy import HomeAssistantSnapshotExtension
from syrupy.assertion import SnapshotAssertion

@pytest.fixture
def snapshot(snapshot: SnapshotAssertion) -> SnapshotAssertion:
    """Return snapshot assertion fixture with the Home Assistant extension."""
    return snapshot.use_extension(HomeAssistantSnapshotExtension)
```
Keeps snapshots colocated with tests (`__snapshots__` folder next to test files).

## `load_fixture` — test data files

Fixture JSON/data files must live in a `fixtures/` folder alongside the test file:
```
tests/
  test_sensor.py
  fixtures/
    some_data.json
```
```python
from pytest_homeassistant_custom_component.common import load_fixture
data = load_fixture("some_data.json")
```

## Other setup requirements
- Set `asyncio_mode = auto` in pytest config (pytest.ini / pyproject.toml) since tests are async and use pytest-asyncio.
- Custom integration path resolution: if your integration lives under `custom_components/`, you may need a `custom_components/__init__.py` or `sys.path` adjustment so it's importable in tests.
- Some fixtures (e.g. `recorder_mock`) must be requested/initialized before `enable_custom_integrations` in fixture ordering — check plugin fixture dependency order if using recorder.
