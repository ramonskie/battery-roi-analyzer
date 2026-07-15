# Battery ROI Analyzer

A Home Assistant custom integration (HACS) that simulates the return on
investment (ROI) of a home battery system using your **existing historical
energy data** — no new hardware or real battery control required.

## Purpose

`battery_roi` is a simulator: it reads historical import/export/production
statistics via the Home Assistant Statistics API and runs a configurable
battery charge/discharge model (LFP/NMC presets) against Dutch net-metering
(saldering) scenarios to estimate:

- Payback period
- Annual savings
- Net Present Value (NPV)
- Internal Rate of Return (IRR)
- Recommended battery size

It does **not** control a physical battery — it is a what-if analysis tool.

## Installation

### HACS (recommended)

1. Add this repository as a custom repository in HACS (category: Integration).
2. Install "Battery ROI Analyzer" from HACS.
3. Restart Home Assistant.
4. Go to **Settings → Devices & Services → Add Integration** and search for
   "Battery ROI Analyzer".

### Manual

1. Copy `custom_components/battery_roi/` into your Home Assistant
   `config/custom_components/` directory.
2. Restart Home Assistant.
3. Add the integration via the UI.

## Configuration

Configuration is done entirely through the UI config flow (5 steps):
energy sensors, pricing, battery parameters, simulation period, and results
review. See the [project documentation](docs/) for details once available.

## Quality Scale Target

This integration targets Home Assistant's **Silver** quality scale or higher:

- UI config flow for setup
- Stable `unique_id` per entity/config entry
- `diagnostics` platform support
- Proper `async_unload_entry` cleanup
- Test coverage for config flow and core simulation/finance logic

## Dashboards

Example Lovelace dashboards (bar charts, heatmap, sankey via
[`apexcharts-card`](https://github.com/RomRider/apexcharts-card)) are
provided under `docs/dashboards/` (soft dependency — a frontend resource,
not a Python package).

## License

MIT — see [LICENSE](LICENSE).
