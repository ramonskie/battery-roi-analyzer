---
source: Context7 API (pandas-dev/pandas)
library: pandas
package: pandas
topic: resample/asfreq patterns for energy time series (1/5/15/60min), gap handling
fetched: 2026-07-15T00:00:00Z
official_docs: https://pandas.pydata.org/docs/user_guide/timeseries.html
---

## Basic downsampling with `.resample(freq).agg()`

```python
rng = pd.date_range("1/1/2012", periods=100, freq="s")
ts = pd.Series(np.random.randint(0, 500, len(rng)), index=rng)
ts.resample("5Min").sum()
```
Frequency strings for energy resolutions: `"1min"`/`"1T"`, `"5min"`, `"15min"`, `"60min"`/`"1h"`.

## Upsampling with `asfreq` + fill methods

`.resample(freq).asfreq()` reindexes to the target frequency WITHOUT aggregation — introduces `NaN` for missing timestamps unless a fill method/value is used.

```python
ts[:2].resample("250ms").asfreq()          # raw upsample, NaNs where no data
ts[:2].resample("250ms").ffill()           # forward-fill gaps
ts[:2].resample("250ms").ffill(limit=2)    # cap consecutive fills
```

## Handling sparse/gappy series (missing data)

Resampling a sparse series over its full range can introduce many `NaN` rows if the source has gaps larger than the target frequency:
```python
ts.resample("3min").sum()   # NaN/0 for empty bins depending on agg
```

## `Resampler` upsampling methods (API reference)

| Method | Purpose | Key params |
|---|---|---|
| `Resampler.asfreq(fill_value=None)` | Reindex to freq, no aggregation | `fill_value` for missing |
| `Resampler.ffill(limit=None)` | Forward-fill resampled data | `limit`: max consecutive NaNs filled |
| `Resampler.bfill(limit=None)` | Backward-fill | `limit` |
| `Resampler.nearest(limit=None)` | Nearest-value fill | `limit`: max distance |
| `Resampler.interpolate(method=..., limit=None, limit_direction=...)` | Interpolate gaps | `method`: linear/time/index/values; `limit_direction`: forward/backward/both |

## Recommended pattern for energy data at fixed resolutions

```python
# Downsample raw readings to 15min buckets, sum (energy) or mean (power)
df_15min = df.resample("15min").sum()          # for energy (kWh) accumulation
df_15min_power = df.resample("15min").mean()   # for power (kW) averaging

# Detect/fill small gaps (<= limit consecutive missing periods) after upsampling
df_1min = df.resample("1min").asfreq()
df_1min_filled = df_1min.interpolate(method="time", limit=5)  # cap interpolation across gaps

# Explicitly mark large gaps instead of silently filling
gap_mask = df_1min.isna()
```

Notes:
- For flow/energy quantities (kWh consumed in interval): downsample with `.sum()`.
- For instantaneous quantities (power in kW, SOC %): downsample with `.mean()`.
- Always resample first with `.asfreq()` to expose true gaps before choosing a fill strategy — don't blindly `ffill`/`interpolate` without a `limit`, or long outages get silently fabricated.
