// Battery ROI Analyzer — Lovelace Dashboard Card
// HACS custom card for the battery_roi integration
// Shows key metrics, capacity comparison, and monthly heatmap

import { LitElement, html, css } from "lit";

const CARD_VERSION = "1.0.0";

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function _num(v, decimals = 1) {
  const n = Number(v);
  return Number.isFinite(n) ? n.toFixed(decimals) : "—";
}

function _euro(v) {
  const n = Number(v);
  if (!Number.isFinite(n)) return "—";
  const prefix = n < 0 ? "−€" : "€";
  return prefix + Math.abs(n).toLocaleString("nl-NL", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  });
}

function _pct(v) {
  const n = Number(v);
  return Number.isFinite(n) ? `${_num(n, 1)}%` : "—";
}

function _bool(v) {
  if (v === true || v === "true") return "✓ Yes";
  if (v === false || v === "false") return "✗ No";
  return "—";
}

/* ------------------------------------------------------------------ */
/*  Card definition                                                    */
/* ------------------------------------------------------------------ */

class BatteryRoiCard extends LitElement {
  static get properties() {
    return { hass: {}, config: {} };
  }

  static getStubConfig() {
    return {};
  }

  /* ----- convenience entity getters with configurable overrides ---- */

  get _s() {
    const prefix = this.config.entity_prefix || "sensor.battery_roi";
    const e = (key, def) => this.config[`${key}_entity`] || `${prefix}_${def}`;
    return {
      best_size: e("best_size", "best_size"),
      payback: e("payback", "payback"),
      annual_saving: e("annual_saving", "annual_saving"),
      best_capacity: e("best_capacity", "best_capacity"),
      cycles: e("cycles", "cycles"),
      self_consumption: e("self_consumption", "self_consumption"),
      import_saved: e("import_saved", "import_saved"),
      export_saved: e("export_saved", "export_saved"),
    };
  }

  _st(id) {
    return this.hass?.states?.[id];
  }

  /* ----- styles ---------------------------------------------------- */

  static get styles() {
    return css`
      :host {
        --br-grid-gap: 12px;
        --br-radius: 12px;
        --br-card-bg: var(--paper-card-background-color, #fff);
        --br-text: var(--primary-text-color, #1c1c1c);
        --br-text-secondary: var(--secondary-text-color, #727272);
        --br-accent: var(--accent-color, #ff7300);
        --br-green: #43a047;
        --br-red: #e53935;
        --br-border: var(--divider-color, #e0e0e0);
        display: block;
        font-family: var(--paper-font-body_-_font-family, inherit);
      }

      .card {
        background: var(--br-card-bg);
        border-radius: var(--br-radius);
        padding: 16px;
        box-shadow: var(--ha-card-box-shadow, 0 2px 4px rgba(0, 0, 0, 0.08));
      }

      /* ---- header ---- */
      .header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 16px;
        padding-bottom: 12px;
        border-bottom: 1px solid var(--br-border);
      }
      .header h2 {
        margin: 0;
        font-size: 18px;
        font-weight: 600;
        color: var(--br-text);
        display: flex;
        align-items: center;
        gap: 8px;
      }
      .header .version {
        font-size: 11px;
        color: var(--br-text-secondary);
        background: var(--br-border);
        padding: 2px 6px;
        border-radius: 4px;
      }
      .header .updated {
        font-size: 12px;
        color: var(--br-text-secondary);
      }

      /* ---- stat grid ---- */
      .grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
        gap: var(--br-grid-gap);
        margin-bottom: 16px;
      }
      .stat {
        background: var(--br-border);
        border-radius: var(--br-radius);
        padding: 12px;
        text-align: center;
        transition: transform 0.15s;
      }
      .stat:hover {
        transform: translateY(-2px);
      }
      .stat .value {
        font-size: 22px;
        font-weight: 700;
        color: var(--br-text);
        line-height: 1.2;
      }
      .stat .value.green {
        color: var(--br-green);
      }
      .stat .value.red {
        color: var(--br-red);
      }
      .stat .value.accent {
        color: var(--br-accent);
      }
      .stat .label {
        font-size: 11px;
        color: var(--br-text-secondary);
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-top: 4px;
      }

      /* ---- section ---- */
      .section-title {
        font-size: 14px;
        font-weight: 600;
        color: var(--br-text);
        margin: 20px 0 12px;
        padding-bottom: 6px;
        border-bottom: 1px solid var(--br-border);
      }

      /* ---- capacity bar chart ---- */
      .chart-wrap {
        overflow-x: auto;
        padding: 4px 0 8px;
      }
      .chart-table {
        width: 100%;
        border-collapse: collapse;
        min-width: 420px;
      }
      .chart-table th {
        text-align: left;
        font-size: 11px;
        color: var(--br-text-secondary);
        padding: 0 0 4px 0;
        font-weight: 500;
      }
      .chart-table td {
        padding: 2px 0;
        vertical-align: middle;
      }
      .chart-table .cap-label {
        font-size: 12px;
        font-weight: 600;
        color: var(--br-text);
        width: 40px;
        white-space: nowrap;
      }
      .bar-track {
        background: var(--br-border);
        border-radius: 4px;
        height: 18px;
        position: relative;
        overflow: hidden;
      }
      .bar-fill {
        height: 100%;
        border-radius: 4px;
        transition: width 0.4s ease;
        min-width: 2px;
      }
      .bar-fill.annual {
        background: var(--br-accent);
      }
      .bar-fill.payback {
        background: var(--br-green);
      }
      .bar-fill.payback.overshoot {
        background: var(--br-red);
      }
      .bar-val {
        font-size: 11px;
        color: var(--br-text-secondary);
        padding-left: 8px;
        white-space: nowrap;
      }
      .chart-legend {
        display: flex;
        gap: 16px;
        font-size: 11px;
        color: var(--br-text-secondary);
        margin-top: 6px;
      }
      .chart-legend .dot {
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 3px;
        margin-right: 4px;
        vertical-align: middle;
      }

      /* ---- monthly heatmap ---- */
      .heatmap {
        display: grid;
        grid-template-columns: 60px repeat(auto-fill, minmax(28px, 1fr));
        gap: 2px;
        align-items: end;
        margin-top: 6px;
      }
      .heatmap .hm-label {
        font-size: 10px;
        color: var(--br-text-secondary);
        text-align: right;
        padding-right: 6px;
        line-height: 28px;
      }
      .hm-cell {
        width: 100%;
        aspect-ratio: 1;
        border-radius: 3px;
        position: relative;
        cursor: pointer;
      }
      .hm-cell:hover::after {
        content: attr(data-tooltip);
        position: absolute;
        bottom: 110%;
        left: 50%;
        transform: translateX(-50%);
        background: var(--br-text);
        color: var(--br-card-bg);
        font-size: 10px;
        padding: 3px 6px;
        border-radius: 4px;
        white-space: nowrap;
        z-index: 10;
        pointer-events: none;
      }
      .hm-legend {
        display: flex;
        align-items: center;
        gap: 4px;
        font-size: 10px;
        color: var(--br-text-secondary);
        margin-top: 8px;
        justify-content: flex-end;
      }
      .hm-legend .hm-swatch {
        width: 14px;
        height: 14px;
        border-radius: 2px;
        display: inline-block;
      }

      /* ---- lifecycle info ---- */
      .lifecycle {
        font-size: 12px;
        color: var(--br-text-secondary);
        margin-top: 12px;
        padding-top: 10px;
        border-top: 1px solid var(--br-border);
        display: flex;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 8px;
      }
    `;
  }

  /* ----- render ---------------------------------------------------- */

  render() {
    const s = this._s;
    const bestSizeSt = this._st(s.best_size);
    const paybackSt = this._st(s.payback);
    const annualSt = this._st(s.annual_saving);

    const byCap = bestSizeSt?.attributes?.by_capacity;
    const monthly = bestSizeSt?.attributes?.monthly_data;

    const paybackAttrs = paybackSt?.attributes || {};
    const paybackVal = paybackSt?.state;
    const withinLifetime = paybackAttrs.within_lifetime;

    return html`
      <ha-card class="card">
        ${this._render_header(bestSizeSt)}
        ${this._render_stats(paybackVal, paybackAttrs, annualSt)}
        ${this._render_secondary_stats(s)}
        ${byCap ? this._render_chart(byCap) : ""}
        ${monthly ? this._render_heatmap(monthly) : ""}
        ${this._render_lifecycle(paybackAttrs)}
      </ha-card>
    `;
  }

  /* ======================== sub-renderers ========================== */

  _render_header(bestSizeSt) {
    const updated = bestSizeSt?.last_updated
      ? new Date(bestSizeSt.last_updated).toLocaleString("nl-NL", {
          day: "numeric",
          month: "short",
          hour: "2-digit",
          minute: "2-digit",
        })
      : "";
    return html`
      <div class="header">
        <h2>
          <span>⚡ Battery ROI</span>
          <span class="version">v${CARD_VERSION}</span>
        </h2>
        <span class="updated">${updated}</span>
      </div>
    `;
  }

  _render_stats(paybackVal, paybackAttrs, annualSt) {
    const pb = _num(paybackVal, 1);
    const withinLifetime = paybackAttrs.within_lifetime;
    const pbClass = withinLifetime ? "green" : "red";

    const annual = annualSt?.state ?? "—";

    const netClass =
      Number(paybackAttrs.net_saving_eur) >= 0 ? "green" : "red";

    return html`
      <div class="grid">
        <div class="stat">
          <div class="value accent">
            ${_num(this._st(this._s.best_size)?.state, 1)}
          </div>
          <div class="label">Best Size (kWh)</div>
        </div>
        <div class="stat">
          <div class="value ${pbClass}">${pb}</div>
          <div class="label">Payback (yr)</div>
        </div>
        <div class="stat">
          <div class="value green">€${_num(annual, 0)}</div>
          <div class="label">Annual Saving</div>
        </div>
        <div class="stat">
          <div class="value ${netClass}">
            ${_euro(paybackAttrs.net_saving_eur)}
          </div>
          <div class="label">Net Result (life)</div>
        </div>
      </div>
    `;
  }

  _render_secondary_stats(s) {
    return html`
      <div class="grid">
        <div class="stat">
          <div class="value">${_pct(this._st(s.self_consumption)?.state)}</div>
          <div class="label">Self-Consumption</div>
        </div>
        <div class="stat">
          <div class="value">${_num(this._st(s.cycles)?.state, 1)}</div>
          <div class="label">Cycles / Year</div>
        </div>
        <div class="stat">
          <div class="value">${_num(this._st(s.import_saved)?.state, 0)}</div>
          <div class="label">Import Saved (kWh/yr)</div>
        </div>
        <div class="stat">
          <div class="value">${_num(this._st(s.export_saved)?.state, 0)}</div>
          <div class="label">Export Saved (kWh/yr)</div>
        </div>
      </div>
    `;
  }

  /* ----- capacity comparison bar chart ----------------------------- */

  _render_chart(byCap) {
    const caps = Object.entries(byCap)
      .map(([k, v]) => ({ cap: k.replace("_", "."), ...v }))
      .sort((a, b) => Number(a.cap) - Number(b.cap));

    const maxPayback = Math.max(
      ...caps.map((c) => (c.payback_years != null ? c.payback_years : 0)),
      1,
    );
    const maxAnnual = Math.max(
      ...caps.map((c) => c.annual_saving_eur ?? 0),
      1,
    );

    return html`
      <div class="section-title">Capacity Comparison</div>
      <div class="chart-wrap">
        <table class="chart-table">
          <thead>
            <tr>
              <th>kWh</th>
              <th>Annual Saving</th>
              <th></th>
              <th>Payback</th>
              <th></th>
              <th>ROI</th>
            </tr>
          </thead>
          <tbody>
            ${caps.map(
              (c) => html`
                <tr>
                  <td class="cap-label">${c.cap}</td>
                  <td style="width:35%">
                    <div class="bar-track">
                      <div
                        class="bar-fill annual"
                        style="width:${((c.annual_saving_eur ?? 0) / maxAnnual) * 100}%"
                      ></div>
                    </div>
                  </td>
                  <td class="bar-val">
                    €${_num(c.annual_saving_eur, 0)}
                  </td>
                  <td style="width:35%">
                    <div class="bar-track">
                      <div
                        class="bar-fill payback ${c.payback_years != null &&
                        c.payback_years > 20
                          ? "overshoot"
                          : ""}"
                        style="width:${Math.min(
                          ((c.payback_years ?? maxPayback) / maxPayback) * 100,
                          100,
                        )}%"
                      ></div>
                    </div>
                  </td>
                  <td class="bar-val">
                    ${c.payback_years != null
                      ? `${_num(c.payback_years, 1)} yr`
                      : "∞"}
                  </td>
                  <td class="bar-val">
                    ${c.roi_pct != null ? `${_num(c.roi_pct, 1)}%` : "—"}
                  </td>
                </tr>
              `,
            )}
          </tbody>
        </table>
      </div>
      <div class="chart-legend">
        <span><span class="dot" style="background:var(--br-accent)"></span>Annual Saving</span>
        <span><span class="dot" style="background:var(--br-green)"></span>Payback</span>
      </div>
    `;
  }

  /* ----- monthly heatmap ------------------------------------------- */

  _render_heatmap(monthly) {
    const months = Object.entries(monthly).sort(([a], [b]) => a.localeCompare(b));
    const maxVal = Math.max(
      ...months.map(([, d]) => Math.max(d.battery_out_kwh ?? 0, d.battery_in_kwh ?? 0)),
      1,
    );

    const intensity = (v) => Math.min(Math.round(((v ?? 0) / maxVal) * 10), 10);

    return html`
      <div class="section-title">Monthly Battery Usage (kWh)</div>
      <div class="heatmap">
        <span class="hm-label"></span>
        <span class="hm-label" style="text-align:center">In</span>
        <span class="hm-label" style="text-align:center">Out</span>
        ${months.map(
          ([key, d]) => html`
            <span class="hm-label">${key}</span>
            <div
              class="hm-cell"
              style="background:var(--br-accent);opacity:${0.1 +
              intensity(d.battery_in_kwh) * 0.08}"
              data-tooltip="${key} in: ${_num(d.battery_in_kwh, 0)} kWh"
            ></div>
            <div
              class="hm-cell"
              style="background:var(--br-green);opacity:${0.1 +
              intensity(d.battery_out_kwh) * 0.08}"
              data-tooltip="${key} out: ${_num(d.battery_out_kwh, 0)} kWh"
            ></div>
          `,
        )}
      </div>
      <div class="hm-legend">
        <span class="hm-swatch" style="background:var(--br-accent);opacity:0.8"></span> Charged
        <span class="hm-swatch" style="background:var(--br-green);opacity:0.8"></span> Discharged
        <span style="margin-left:auto">Low ▸ High</span>
      </div>
    `;
  }

  /* ----- lifecycle info -------------------------------------------- */

  _render_lifecycle(attrs) {
    const upfront = attrs.upfront_cost_eur;
    const withinLifetime = attrs.within_lifetime;
    return html`
      <div class="lifecycle">
        <span>Upfront: ${upfront != null ? _euro(upfront) : "—"}</span>
        <span>Pays back within life: ${_bool(withinLifetime)}</span>
        <span>Annual: €${_num(attrs.annual_saving_eur, 0)}</span>
      </div>
    `;
  }

  /* ----- card metadata (for HA editor) ----------------------------- */

  static async getConfigElement() {
    // Basic editor: just title + entity prefix
    const el = document.createElement("div");
    el.innerHTML = `
      <style>
        .br-edit { padding: 8px; }
        .br-edit label { display:block; margin:8px 0 4px; font-size:12px; color:var(--secondary-text-color); }
        .br-edit input { width:100%; box-sizing:border-box; }
      </style>
      <div class="br-edit">
        <label>Title (optional)</label>
        <input id="title" placeholder="Battery ROI" />
        <label>Entity prefix (default: sensor.battery_roi)</label>
        <input id="prefix" placeholder="sensor.battery_roi" />
      </div>
    `;
    el.querySelector("#title").addEventListener("change", () => {
      el._config = { ...el._config, title: el.querySelector("#title").value || undefined };
      el.dispatchEvent(new Event("config-changed", { bubbles: true }));
    });
    el.querySelector("#prefix").addEventListener("change", () => {
      el._config = { ...el._config, entity_prefix: el.querySelector("#prefix").value || undefined };
      el.dispatchEvent(new Event("config-changed", { bubbles: true }));
    });
    el.setConfig = (cfg) => {
      el._config = cfg;
      el.querySelector("#title").value = cfg?.title || "";
      el.querySelector("#prefix").value = cfg?.entity_prefix || "";
    };
    return el;
  }
}

customElements.define("battery-roi-card", BatteryRoiCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "battery-roi-card",
  name: "Battery ROI Analyzer",
  description: "Dashboard card showing battery ROI metrics, capacity comparison, and monthly usage heatmap",
  preview: true,
  documentationURL: "https://github.com/ramonskie/battery-roi-analyzer",
});
