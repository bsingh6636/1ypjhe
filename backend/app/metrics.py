"""Pure error metrics and the hourly alignment rule. No I/O.

Alignment: WINDFOR is hourly, FUELHH is half-hourly. For forecast hour h we compare against the mean of the
two half-hour actuals starting at h and h+30min. If either half-hour is missing, the hour is excluded.
Forecasts are never interpolated or duplicated to half-hours.

Sign convention: error = forecast - actual. Positive means wind was over-forecast.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

HALF_HOUR = timedelta(minutes=30)


def hourly_mean_actual(hour: datetime, actuals: Mapping[datetime, float]) -> float | None:
    a = actuals.get(hour)
    b = actuals.get(hour + HALF_HOUR)
    if a is None or b is None:
        return None
    return (a + b) / 2.0


def percentile(values: Sequence[float], q: float) -> float:
    """Empirical percentile with linear interpolation between order statistics (numpy 'linear')."""
    if not values:
        raise ValueError("percentile of empty sample")
    if not 0.0 <= q <= 1.0:
        raise ValueError("q must be within [0, 1]")
    s = sorted(values)
    rank = q * (len(s) - 1)
    lo = math.floor(rank)
    hi = math.ceil(rank)
    if lo == hi:
        return float(s[lo])
    return float(s[lo] + (s[hi] - s[lo]) * (rank - lo))


@dataclass(frozen=True)
class ErrorMetrics:
    n: int
    mae_mw: float
    rmse_mw: float
    bias_mw: float
    p90_abs_mw: float


def compute_metrics(errors: Sequence[float]) -> ErrorMetrics | None:
    """Aggregate over the pooled errors. Returns None for an empty sample rather than a misleading zero."""
    n = len(errors)
    if n == 0:
        return None
    abs_errors = [abs(e) for e in errors]
    return ErrorMetrics(
        n=n,
        mae_mw=sum(abs_errors) / n,
        rmse_mw=math.sqrt(sum(e * e for e in errors) / n),
        bias_mw=sum(errors) / n,
        p90_abs_mw=percentile(abs_errors, 0.9),
    )


def energy_mwh(values_mw: Sequence[float], interval_hours: float) -> float:
    """MW x hours = MWh. Callers must only pass matched intervals so missing coverage stays visible."""
    return sum(values_mw) * interval_hours
