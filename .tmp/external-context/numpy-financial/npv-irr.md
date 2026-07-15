---
source: numpy.org official docs + GitHub source (numpy/numpy-financial)
library: numpy-financial
package: numpy-financial
topic: npv and irr signatures, params, return type, nan behavior
fetched: 2026-07-15T00:00:00Z
official_docs: https://numpy.org/numpy-financial/latest/
---

## `numpy_financial.npv(rate, values)`

- **rate** (scalar/float): discount rate per period. Must match the interval between cashflow events in `values` (e.g. annual rate if cashflows are annual).
- **values** (array_like, shape (M,)): cashflow series. Convention: investments/deposits negative, income/withdrawals positive. `values[0]` is typically the initial investment (negative).
- **Returns**: `float` — NPV of the series at `rate`.
- Formula: `sum(values[t] / (1+rate)**t for t in range(M))`, t starting at 0 (present).
- No nan-producing failure mode — pure summation, always returns a number (barring nan/inf inputs).

```python
>>> npf.npv(0.08, [-40000, 5000, 8000, 12000, 30000]).round(5)
3065.22267
```

## `numpy_financial.irr(values, *, raise_exceptions=False, selection_logic=...)`

- **values** (array_like, shape (N,)): cashflow series per period. Convention same as npv: `values[0]` (initial investment) typically negative, subsequent net withdrawals/savings positive.
- **raise_exceptions** (bool, default False): if True, raises `NoRealSolutionError` when no real root exists instead of returning nan.
- **selection_logic** (callable, optional): used when polynomial has multiple real roots of the same sign — picks which root to return (default picks based on sign-consistency heuristic).
- **Returns**: `float` (or ndarray of float64 for 2D input) — the periodic IRR satisfying `sum(values[t]/(1+irr)**t) = 0`.
- `decimal.Decimal` not supported for irr.

### NaN / no-real-solution behavior (from source, `_financial.py`)
```python
# If no real solution
if len(eirr) == 0:
    if raise_exceptions:
        raise NoRealSolutionError("No real solution is found for IRR.")
    irr_results[i] = np.nan
# If only one real solution
elif len(eirr) == 1:
    irr_results[i] = eirr[0]
else:
    irr_results[i] = selection_logic(eirr)  # multiple real roots, pick one
```

- **Default behavior (`raise_exceptions=False`)**: returns `np.nan` when the cashflow polynomial has no real root (e.g. all cashflows same sign, or degenerate series). This is a `float` nan — check with `math.isnan(result)` or `np.isnan(result)`.
- If `raise_exceptions=True`: raises `numpy_financial.NoRealSolutionError` instead.
- Multiple real roots: internal `_irr_default_selection` checks if all roots share the same sign as `eirr[0]`; picks accordingly (heuristic — not guaranteed "the" economically correct root for pathological cashflow series with sign changes >1).

```python
>>> npf.irr([-100, 39, 59, 55, 20])  # 0.28095
>>> npf.irr([-100, 100, 0, -7])       # -0.0833 (still real solution)
```

## Guidance for `finance.py` (battery ROI, values[0]=-investment, values[1:]=annual savings)

1. Cashflow shape `[-initial_investment] + [annual_savings]*lifetime_years` is a standard single-sign-change series (negative then positive) → almost always has exactly one real IRR root. NaN case mainly arises if:
   - annual savings are negative or zero throughout (no payback ever) → no real root → `npf.irr` returns `nan`.
   - all-positive or all-negative series (degenerate/no investment) → `nan`.
2. Recommended pattern:
   ```python
   import numpy_financial as npf
   import math

   irr = npf.irr(values)
   if irr is None or (isinstance(irr, float) and math.isnan(irr)):
       # no real solution — battery investment never pays back within lifetime,
       # or degenerate cashflow. Surface as None / "N/A" to HA sensor, not 0 or error.
       irr = None
   ```
3. Don't use `raise_exceptions=True` unless you want to catch `NoRealSolutionError` explicitly and handle it as the same "no payback" case — either approach works; nan-check is simpler for a sensor value that should show "unavailable"/"unknown" in Home Assistant.
4. `npv` never returns nan under normal conditions — safe to compute unconditionally alongside irr.
</content>
