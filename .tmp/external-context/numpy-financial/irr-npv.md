---
source: Context7 API + official docs (numpy.org/numpy-financial)
library: numpy-financial
package: numpy-financial
topic: irr, npv exact signatures, edge cases
fetched: 2026-07-15T00:00:00Z
official_docs: https://numpy.org/numpy-financial/latest/
---

## `numpy_financial.npv(rate, values)`

```
numpy_financial.npv(rate, values)
```
- **rate**: scalar — discount rate per period.
- **values**: array_like, shape (M,) — cash flows. `values[0]` is typically negative (initial investment). Convention: deposits negative, withdrawals positive.
- **Returns**: `float` — NPV = Σ_{t=0}^{M-1} values[t] / (1+rate)^t
- No decimal.Decimal support noted for npv (unlike irr where it's explicit).
- **Note**: npv assumes cashflow at t=0 is "now" (present), not end-of-period. For end-of-period-only series, zero out `values[0]` and add initial investment separately (see example).

```python
import numpy_financial as npf
rate, cashflows = 0.08, [-40_000, 5_000, 8_000, 12_000, 30_000]
npf.npv(rate, cashflows).round(5)
# 3065.22267
```

## `numpy_financial.irr(values)`

```
numpy_financial.irr(values)
```
- **values**: array_like, shape (N,) — cash flows per period. First element typically negative (initial investment).
- **Returns**: `float` — the rate `r` solving Σ v_t / (1+r)^t = 0.
- **`decimal.Decimal` type is NOT supported.**
- **Edge cases / no solution**:
  - If no real solution exists (e.g., no sign change in cashflows, or the polynomial root-finder fails to converge), `irr` returns `numpy.nan`. Always check `np.isnan(result)` before using.
  - Multiple sign changes in cashflows → multiple real roots possible (per Descartes' rule of signs); numpy-financial returns whichever root its underlying polynomial-roots solver picks (not guaranteed to be the "intended" economic one) — validate against expected range/sign.
  - All-positive or all-negative cashflows (no sign change) → typically returns `nan` (no rate makes NPV zero).
  - Uses `numpy.roots` on the cashflow polynomial internally; large/ill-conditioned cashflow series can produce numerically unstable or complex roots (only real, in-range roots considered).

```python
import numpy_financial as npf
npf.irr([-250000, 100000, 150000, 200000, 250000, 300000])
# 0.5672303344358536

round(npf.irr([-100, 39, 59, 55, 20]), 5)   # 0.28095
round(npf.irr([-100, 0, 0, 74]), 5)          # -0.0955
round(npf.irr([-100, 100, 0, -7]), 5)        # -0.0833
round(npf.irr([-100, 100, 0, 7]), 5)         # 0.06206
round(npf.irr([-5, 10.5, 1, -8, 1]), 5)      # 0.0886
```

### Practical edge-case handling pattern
```python
result = npf.irr(cashflows)
if np.isnan(result):
    # no real solution found — cashflows may have no sign change,
    # or polynomial roots are all complex/out of range
    ...
```
