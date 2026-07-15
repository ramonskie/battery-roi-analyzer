# Battery ROI Analyzer — Example Lovelace Dashboards

These YAML files are **examples**, not turnkey configs. Copy the card
blocks into your own dashboard (Settings → Dashboards → Edit → raw
YAML editor), adjust entity IDs to match your config entry.

## Soft dependency: `apexcharts-card`

Every bar/gauge/heatmap example here uses
[`apexcharts-card`](https://github.com/RomRider/apexcharts-card), a
**frontend-only Lovelace custom card** installed via HACS
(HACS → Frontend → search "ApexCharts Card"). It is **not** a Python
dependency of this integration — `manifest.json` does not list it,
and the integration works fully without it. If it isn't installed,
these dashboard YAML examples simply won't render; all sensor
entities are still available for use in built-in HA cards
(`entities`, `gauge`, `statistics-graph`, etc.).

For `06-sankey.yaml`, install
[`plotly-graph`](https://github.com/dbuezas/lovelace-plotly-graph-card)
via HACS (apexcharts-card has no native sankey series).

## Files

| File | Chart | Card |
|---|---|---|
| `01-annual-saving.yaml` | Annual saving € per battery size (bar) | apexcharts-card |
| `02-payback-period.yaml` | Payback period per battery size (bar) | apexcharts-card |
| `03-self-consumption.yaml` | Self-consumption % (gauge + bar) | apexcharts-card |
| `04-cycles-per-year.yaml` | Cycles/year (bar) | apexcharts-card |
| `05-monthly-heatmap.yaml` | Monthly PV/battery/export/import heatmap | apexcharts-card (heatmap series) |
| `06-sankey.yaml` | Energy flow PV → Battery → Self-consumption → Grid | plotly-graph |

## Data attributes

Cards 01, 02, and 05 read from `sensor.battery_roi_best_size`'s
`extra_state_attributes`:

- **`by_capacity`**: Dict keyed by capacity (underscore-separated,
  e.g. `7_5` for 7.5 kWh). Each value contains `annual_saving_eur`,
  `payback_years`, `npv_eur`, `roi_pct`, `self_consumption_pct`,
  `cycles_per_year`, `reduced_grid_import_kwh`, `reduced_export_kwh`.
- **`monthly_data`**: Dict keyed by `YYYY-MM`. Each value contains
  `pv_kwh`, `battery_in_kwh`, `battery_out_kwh`, `imported_kwh`,
  `exported_kwh` aggregated from the simulation's per-timestep data
  for the best-by-ROI battery capacity.

No additional sensors or persistence needed for these attributes —
they are computed fresh each time the coordinator refreshes.

## Setup instructions

1. Install `apexcharts-card` via HACS (Frontend section), restart/clear
   cache after install.
2. For `06-sankey.yaml`, also install `plotly-graph` via HACS.
3. In each YAML file, replace `sensor.battery_roi_*` entity IDs with
   your actual config-entry-specific entity IDs if you have more than
   one config entry.
4. Paste the card block(s) into a dashboard view via the raw YAML
   editor, or use "Edit dashboard" → "+ Add card" → "Manual" and paste
   a single card block at a time.
