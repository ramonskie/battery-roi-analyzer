"""Shared pytest fixtures for the battery_roi integration test suite."""

from __future__ import annotations

from typing import Any

import pandas as pd
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.battery_roi.const import DOMAIN


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable loading of custom integrations for every test in this suite.

    Required by ``pytest-homeassistant-custom-component`` — without this,
    Home Assistant refuses to set up custom (non-core) integrations during
    tests, causing ``config_flow`` tests to fail with "integration not
    found".
    """
    return None


@pytest.fixture
def sample_energy_dataframe() -> pd.DataFrame:
    """Build a small, evenly-spaced (hourly) PV/consumption/import/export DataFrame.

    Alternates two-hour surplus/shortfall blocks so simulator tests can
    exercise both charge and discharge legs deterministically:

    * hour 0: pv=5, verbruik=1 -> surplus=4 (export=4, import=0)
    * hour 1: pv=0, verbruik=3 -> shortfall=3 (import=3, export=0)
    * hour 2: pv=5, verbruik=1 -> surplus=4 (export=4, import=0)
    * hour 3: pv=0, verbruik=3 -> shortfall=3 (import=3, export=0)

    Import/export here reflect the *no-battery baseline* grid flows that
    ``simulate_battery`` corrects for charged/discharged energy.
    """
    index = pd.date_range("2026-01-01", periods=4, freq="1h")
    return pd.DataFrame(
        {
            "pv": [5.0, 0.0, 5.0, 0.0],
            "verbruik": [1.0, 3.0, 1.0, 3.0],
            "import": [0.0, 3.0, 0.0, 3.0],
            "export": [4.0, 0.0, 4.0, 0.0],
        },
        index=index,
    )


@pytest.fixture
def mock_config_entry_factory() -> Any:
    """Return a factory building ``MockConfigEntry`` objects for this domain.

    Usage: ``entry = mock_config_entry_factory(data={...})``.
    """

    def _factory(**kwargs: Any) -> MockConfigEntry:
        kwargs.setdefault("domain", DOMAIN)
        kwargs.setdefault("title", "Battery ROI Analyzer")
        return MockConfigEntry(**kwargs)

    return _factory
