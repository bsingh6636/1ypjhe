from datetime import UTC, date, datetime, time

import pytest

from backend.app.selection import (
    ConflictingForecastError,
    ForecastRecord,
    cutoff_utc,
    delivery_window,
    expected_hours,
    select_latest,
)

T = datetime(2026, 1, 11, 12, 0, tzinfo=UTC)  # a delivery hour


def rec(publish: str, mw: float, start: datetime = T) -> ForecastRecord:
    return ForecastRecord(datetime.fromisoformat(publish).replace(tzinfo=UTC), start, mw)


def test_latest_at_or_before_cutoff_wins_and_later_is_ignored():
    cutoff = datetime(2026, 1, 10, 9, 20, tzinfo=UTC)
    records = [
        rec("2026-01-10T07:30", 100.0),
        rec("2026-01-10T09:20", 110.0),  # exactly at cutoff: eligible
        rec("2026-01-10T09:30", 999.0),  # after cutoff: must never be chosen, however accurate
    ]
    chosen = select_latest(records, cutoff)
    assert chosen[T].generation_mw == 110.0
    assert chosen[T].publish_time == datetime(2026, 1, 10, 9, 20, tzinfo=UTC)


def test_order_independence():
    cutoff = datetime(2026, 1, 10, 9, 20, tzinfo=UTC)
    records = [rec("2026-01-10T09:00", 3.0), rec("2026-01-10T02:30", 1.0), rec("2026-01-10T07:30", 2.0)]
    assert select_latest(records, cutoff)[T].generation_mw == 3.0
    assert select_latest(list(reversed(records)), cutoff)[T].generation_mw == 3.0


def test_previous_day_fallback_when_no_run_on_decision_day():
    cutoff = datetime(2026, 1, 10, 9, 20, tzinfo=UTC)
    chosen = select_latest([rec("2026-01-09T22:30", 42.0)], cutoff)
    assert chosen[T].generation_mw == 42.0


def test_no_eligible_record_gives_gap_not_zero():
    cutoff = datetime(2026, 1, 10, 9, 20, tzinfo=UTC)
    assert select_latest([rec("2026-01-10T09:21", 5.0)], cutoff) == {}


def test_identical_duplicates_are_idempotent_but_conflicts_raise():
    cutoff = datetime(2026, 1, 10, 9, 20, tzinfo=UTC)
    same = [rec("2026-01-10T07:30", 7.0), rec("2026-01-10T07:30", 7.0)]
    assert select_latest(same, cutoff)[T].generation_mw == 7.0
    with pytest.raises(ConflictingForecastError):
        select_latest([rec("2026-01-10T07:30", 7.0), rec("2026-01-10T07:30", 8.0)], cutoff)


def test_irregular_publish_time_is_handled_by_timestamp_not_schedule():
    cutoff = datetime(2026, 1, 10, 12, 30, tzinfo=UTC)
    records = [rec("2026-01-10T11:30", 1.0), rec("2026-01-10T12:25", 2.0)]
    assert select_latest(records, cutoff)[T].generation_mw == 2.0


def test_zero_forecast_is_a_valid_value():
    cutoff = datetime(2026, 1, 10, 9, 20, tzinfo=UTC)
    assert select_latest([rec("2026-01-10T07:30", 0.0)], cutoff)[T].generation_mw == 0.0


def test_cutoff_in_january_is_gmt_and_in_summer_is_bst():
    assert cutoff_utc(date(2026, 1, 10), time(9, 20)) == datetime(2026, 1, 10, 9, 20, tzinfo=UTC)
    assert cutoff_utc(date(2026, 7, 10), time(9, 20)) == datetime(2026, 7, 10, 8, 20, tzinfo=UTC)


def test_delivery_window_january_31_rolls_into_february():
    start, end = delivery_window(date(2026, 1, 31))
    assert start == datetime(2026, 2, 1, 0, 0, tzinfo=UTC)
    assert end == datetime(2026, 2, 2, 0, 0, tzinfo=UTC)
    assert len(expected_hours(start, end)) == 24


def test_expected_hours_follow_local_day_length_across_dst():
    start, end = delivery_window(date(2026, 3, 28))  # delivery 29 March 2026, clocks go forward
    assert len(expected_hours(start, end)) == 23
    start, end = delivery_window(date(2026, 10, 24))  # delivery 25 October 2026, clocks go back
    assert len(expected_hours(start, end)) == 25
