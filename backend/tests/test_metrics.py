import math
from datetime import UTC, datetime, timedelta

import pytest

from backend.app.metrics import compute_metrics, energy_mwh, hourly_mean_actual, percentile


def test_hand_calculated_metrics():
    # errors: forecast - actual
    errors = [100.0, -50.0, 0.0, 250.0]
    m = compute_metrics(errors)
    assert m is not None
    assert m.n == 4
    assert m.mae_mw == pytest.approx((100 + 50 + 0 + 250) / 4)  # 100
    assert m.rmse_mw == pytest.approx(math.sqrt((100**2 + 50**2 + 0 + 250**2) / 4))  # ~137.84
    assert m.bias_mw == pytest.approx((100 - 50 + 0 + 250) / 4)  # 75, positive = over-forecast
    # abs errors sorted: 0, 50, 100, 250 -> rank 0.9*3 = 2.7 -> 100 + 0.7*150 = 205
    assert m.p90_abs_mw == pytest.approx(205.0)


def test_negative_only_errors_keep_sign_in_bias():
    m = compute_metrics([-10.0, -30.0])
    assert m is not None
    assert m.bias_mw == -20.0
    assert m.mae_mw == 20.0


def test_empty_sample_returns_none_not_zero():
    assert compute_metrics([]) is None


def test_percentile_linear_interpolation_and_bounds():
    vals = list(range(1, 11))  # 1..10
    assert percentile(vals, 0.9) == pytest.approx(9.1)
    assert percentile(vals, 0.0) == 1
    assert percentile(vals, 1.0) == 10
    assert percentile([7.0], 0.5) == 7.0
    with pytest.raises(ValueError):
        percentile([], 0.5)


def test_hourly_mean_requires_both_half_hours():
    h = datetime(2026, 1, 11, 3, 0, tzinfo=UTC)
    both = {h: 100.0, h + timedelta(minutes=30): 300.0}
    assert hourly_mean_actual(h, both) == 200.0
    assert hourly_mean_actual(h, {h: 100.0}) is None
    assert hourly_mean_actual(h, {}) is None


def test_zero_actual_is_valid():
    h = datetime(2026, 1, 11, 3, 0, tzinfo=UTC)
    assert hourly_mean_actual(h, {h: 0.0, h + timedelta(minutes=30): 0.0}) == 0.0


def test_energy_is_mw_times_hours():
    assert energy_mwh([100.0, 200.0], 1.0) == 300.0
    assert energy_mwh([100.0, 200.0], 0.5) == 150.0
    assert energy_mwh([], 1.0) == 0.0
