---
category: standard
type: code-quality
updated: 2026-07-15
codebase_ref: custom_components/battery_roi/
---

# Code Quality Standards

## Typing
- Type hints mandatory everywhere. Use PEP 604 union syntax (`X | None`), py3.11+ (matches HA core).

## Async
- All I/O async/await. No blocking calls in event loop.
- Blocking work (numpy/pandas simulation, file/CSV parsing) → `hass.async_add_executor_job(...)`.

## HA Integration Quality Scale
- Target **Silver** minimum:
  - `config_flow` for setup
  - stable `unique_id` per entity/config entry
  - `diagnostics` platform implemented
  - proper `async_unload_entry` cleanup
  - test coverage for config flow + core logic

## Coordinator Pattern
- Use `DataUpdateCoordinator` for polling/recompute cycles (simulation refresh, statistics pulls).

## Data Structures
- Prefer `dataclasses` (or `attrs` if richer validation needed) for config models and simulation result objects.

## Docstrings
- Google style. Minimal, high-signal — document intent/params/returns, not obvious restatements.

## Linting
- `ruff` + `mypy`. Follow HA core's ruff config conventions (import order, line length, no wildcard imports).

## Testing
- `pytest` + `pytest-homeassistant-custom-component`.
- Priority coverage: `simulator.py` and `finance.py` (core business logic).

## Recorder / Statistics Access
- Never query SQLite/recorder DB directly.
- Use Statistics API only: `recorder.statistics.statistics_during_period` via the recorder instance.

## Secrets & Privacy
- Never log API keys, tokens, or PII.
