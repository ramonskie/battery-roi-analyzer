# Task Context: Home Assistant Battery ROI Analyzer (HACS)

Session ID: 2026-07-15-battery-roi-analyzer
Created: 2026-07-15T00:00:00Z
Status: in_progress

## Current Request
Build a HACS custom integration `battery_roi` for Home Assistant that simulates
home battery ROI using existing historical energy data (via the HA Statistics
API — no direct Recorder DB/SQL queries). Simulator only, does not control a
real battery. Full spec: config flow (5 steps), configurable battery model
(LFP/NMC), Dutch net-metering (saldering) scenarios, financial calc (ROI, NPV,
IRR, payback), multi-scenario comparison, sensors, Lovelace dashboard examples
(bar charts, heatmap, sankey via apexcharts-card), daily-cached simulation
recomputed on settings change.

## Context Files (Standards to Follow)
- .opencode/context/core/standards/code-quality.md
- .opencode/context/core/standards/external-libraries.md
- .opencode/context/core/processes/component-planning.md
- .opencode/context/navigation.md

## Reference Files (Source Material to Look At)
- (none yet — greenfield repo, no existing source)

## External Docs Fetched
All fetched, saved under `.tmp/external-context/`:
- `home-assistant-core/config-flow-and-options-flow.md`
- `home-assistant-core/data-update-coordinator.md`
- `home-assistant-core/diagnostics-platform.md`
- `home-assistant-core/repairs-platform.md`
- `home-assistant-core/translations.md`
- `home-assistant-core/recorder-statistics-api.md` (get_instance(hass).async_add_executor_job(...) pattern — mandatory, no direct DB/SQL)
- `home-assistant-core/sensor-entity-basics.md`
- `home-assistant-core/hacs-and-manifest-requirements.md`
- `numpy-financial/irr-npv.md` (npf.irr returns nan if no real solution)
- `pandas/resample-asfreq-energy-timeseries.md` (resample+ffill/interpolate with capped limit)
- `pytest-homeassistant-custom-component/custom-component-test-setup.md` (enable_custom_integrations fixture, MockConfigEntry, asyncio_mode=auto)

## Components
1. HACS scaffolding: manifest.json, hacs.json, README, LICENSE
2. config_flow.py — 5-step config flow (sensors, prices, battery params, sim period, results)
3. statistics.py — HA Statistics API wrapper (async, executor-job wrapped)
4. simulator.py — numpy/pandas battery charge/discharge simulation per timestep
5. finance.py — ROI, NPV, IRR (numpy-financial), payback, saldering scenarios (none/full/phase-out/own tariff/dynamic-via-sensor)
6. coordinator.py — DataUpdateCoordinator, daily cache, recompute on options change
7. sensor.py — sensor.battery_roi_* entities
8. diagnostics.py, repairs.py, services.yaml
9. translations/en.json, translations/nl.json
10. tests/ — pytest + pytest-homeassistant-custom-component, cover simulator.py + finance.py
11. Lovelace dashboard YAML examples (docs/dashboards/) using apexcharts-card for heatmap/sankey

## Constraints
- Statistics API only — never touch Recorder DB/SQLite directly
- numpy-financial dependency for IRR/NPV (confirmed by user)
- Dynamic pricing (Tibber/EnergyZero) = out of scope for v1; user provides a
  sensor entity holding current dynamic price instead
- Dashboard cards: apexcharts-card assumed as soft dependency (documented, not
  a Python dep) for heatmap/sankey visuals
- Target HA Integration Quality Scale: Silver or higher
- Async-first, type hints mandatory, ruff + mypy clean
- Full simulation runs max once/day; recompute triggered on options/config change

## Exit Criteria
- [ ] Repo scaffold matches spec structure (custom_components/battery_roi/...)
- [ ] Config flow completes all 5 steps and creates a config entry
- [ ] Coordinator runs simulation via Statistics API, caches daily
- [ ] Sensors expose required entities (best_size, payback, annual_saving, etc.)
- [ ] Battery model supports LFP/NMC presets + full configurability
- [ ] Financial calc supports saldering scenarios + NPV/IRR via numpy-financial
- [ ] Diagnostics + repairs + translations (en/nl) present
- [ ] Unit tests pass for simulator.py and finance.py
- [ ] Example Lovelace dashboard YAML provided in docs/
