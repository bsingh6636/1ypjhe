# Methodology

## Question the product answers

A GB utility buys day-ahead power to cover the gap between consumer demand and what renewables will produce. Wind is the largest weather-driven component, so the desk needs two things at the moment it decides:

1. the wind generation forecast that was actually available at the cutoff, and
2. a quantified view of how wrong that kind of forecast tends to be.

This pilot answers both for purchase decisions made in January 2026, using only the two Elexon datasets named in the brief.

## Data

| Dataset | Endpoint | Role | Resolution | Fields used |
|---|---|---|---|---|
| WINDFOR | `datasets/WINDFOR/stream` | forecast vintages | hourly `startTime`, many `publishTime` runs | `publishTime`, `startTime`, `generation` (MW) |
| FUELHH, fuelType WIND | `datasets/FUELHH/stream` | metered actuals | half-hourly settlement periods | `startTime`, `generation` (MW) |

Observed facts about the January 2026 data, checked by `scripts/coverage_report.py` and the pre-build data check:

- WINDFOR is published about 8 times a day (02:30, 04:30, 07:30, 09:30, 11:30, 15:30, 18:30, 22:30 UTC in January, with one irregular 12:25 run). Every run published on day D covers the fixed window D-1 21:00 to D+2 21:00 UTC, so a morning run always covers the whole of D+1.
- Historical runs are retrievable by `publishDateTimeFrom/To`, which is what makes a faithful replay possible.
- FUELHH WIND has exactly 48 periods for every day from 1 January to 1 February 2026, no nulls, no duplicates.

The retrieval query window starts on 30 December 2025 so the 1 January decision has its full run history, and ends on 1 February 2026 so the 31 January decision has its delivery-day actuals.

## Definitions

- **Decision date D**: a calendar day in UK time, 1 to 31 January 2026.
- **Cutoff C**: a UK wall-clock time on D. Defaults to 09:20 (EPEX SPOT GB day-ahead gate closure). 09:50 (Nord Pool N2EX) is a preset; any time can be entered. The client's actual exchange and internal deadline are not known, so this is an explicit assumption.
- **Delivery day**: the whole of D+1 in UK time, as 24 hourly intervals (23 or 25 across a clock change; not relevant in January).
- **Eligible forecast for hour t**: the record with the greatest `publishTime` at or before C that has `startTime` t. Formally `F(t, C) = generation of argmax publishTime <= C`. The guard is applied in SQL and again in the pure selection function.
- **Actual for hour t**: the mean of the two FUELHH half-hour values starting at t and t+30 min. Both must exist; otherwise the hour is excluded. Forecasts are never interpolated or duplicated to half-hours.
- **Error**: `e = forecast − actual` in MW. Positive means wind was over-forecast, so a buyer relying on it would be short of energy.

## Metrics

All metrics are pooled over the matched hours in the selection, never averaged across daily values. Every result carries its sample count and exclusion count.

| Metric | Formula | Why |
|---|---|---|
| MAE | mean of abs(e) | typical size of a miss |
| RMSE | sqrt(mean of e²) | sensitive to large misses |
| Bias | mean of e | systematic over- or under-forecasting |
| P90 abs error | 90th percentile of abs(e), linear interpolation | a planning margin: 9 in 10 hours missed by less |
| Energy | sum(MW) × 1 h | MWh over matched hours only |

MAPE is deliberately not shown: it explodes at low wind.

## Cutoff comparison

The optional comparison evaluates two cutoffs on the intersection of hours where both have an eligible forecast and a complete actual, so the two sides are never computed on different samples. Later publication does not necessarily mean better accuracy; the January result shows the 09:30 run improves MAE by only about 26 MW over the 07:30 run.

## What is deliberately not claimed

- This is a historical replay. The month-level error statistics were not available to anyone during January; they are a retrospective evaluation and are kept on a separate view from the decision replay.
- No calibrated predictive interval is offered. That would need a rolling, strictly out-of-sample estimate.
- Elexon FUELHH wind is transmission-metered wind. Embedded wind is not included, so the numbers describe the Elexon-reported series, not every turbine in GB.
- The product does not compute the utility's purchase volume. Demand, portfolio, prices and other generation are outside the supplied data.

## January 2026 headline (snapshot e9a00d8a41e0, cutoff 09:20)

| | Value |
|---|---|
| Matched hours | 744 of 744 |
| MAE | 2,039 MW |
| RMSE | 2,505 MW |
| Bias | +1,748 MW (over-forecast) |
| P90 abs error | 4,098 MW |
| Worst day | decision 27 Jan for delivery 28 Jan: MAE 5,375 MW, every hour over-forecast |

Reproduce with `python scripts/coverage_report.py --compare 09:50`.
