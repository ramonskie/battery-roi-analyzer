---
category: standard
type: external-libraries
updated: 2026-07-15
codebase_ref: custom_components/battery_roi/, requirements*.txt
---

# External Libraries

## Core simulation dependencies (runtime)
- `numpy` — array math for simulation loops
- `pandas` — time-series handling for load/price/battery data
- `numpy-financial` — NPV/IRR/payback calculations for ROI finance logic

## Dev dependency
- `homeassistant` — dev/test only, not shipped; provided by HA runtime at install time

## Optional / dashboard-only
- `apexcharts-card` — Lovelace dashboard card (HACS frontend resource), **not a Python dependency**. Do not add to `requirements` in `manifest.json`.
