"""Pure forecast-selection logic. No I/O, no framework imports; this is what the no-look-ahead tests exercise.

Contract: for decision date D, cutoff C (UK local time on D) and delivery interval t on D+1,
    F(t, C) = generation of the record with the greatest publishTime <= C for that t.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo


@dataclass(frozen=True, order=True)
class ForecastRecord:
    publish_time: datetime
    start_time: datetime
    generation_mw: float


class ConflictingForecastError(ValueError):
    """Two records share (publish_time, start_time) but disagree on the value. Ambiguous; refuse to pick."""


def cutoff_utc(decision_date: date, cutoff: time, tz: str = "Europe/London") -> datetime:
    """The decision instant: `cutoff` wall-clock time in `tz` on the decision date, as a UTC datetime."""
    return datetime.combine(decision_date, cutoff, tzinfo=ZoneInfo(tz)).astimezone(UTC)


def delivery_window(decision_date: date, tz: str = "Europe/London") -> tuple[datetime, datetime]:
    """Half-open UTC window [start, end) covering the whole local calendar day after the decision date."""
    zone = ZoneInfo(tz)
    delivery = decision_date + timedelta(days=1)
    start = datetime.combine(delivery, time(0), tzinfo=zone).astimezone(UTC)
    end = datetime.combine(delivery + timedelta(days=1), time(0), tzinfo=zone).astimezone(UTC)
    return start, end


def expected_hours(start: datetime, end: datetime) -> list[datetime]:
    """Hourly interval starts in [start, end). 24 on a normal day, 23 or 25 across a DST change."""
    hours = []
    t = start
    while t < end:
        hours.append(t)
        t += timedelta(hours=1)
    return hours


def select_latest(records: list[ForecastRecord], cutoff: datetime) -> dict[datetime, ForecastRecord]:
    """Latest eligible record per start_time. Records published after `cutoff` are ignored even if present."""
    chosen: dict[datetime, ForecastRecord] = {}
    for rec in records:
        if rec.publish_time > cutoff:
            continue
        current = chosen.get(rec.start_time)
        if current is None or rec.publish_time > current.publish_time:
            chosen[rec.start_time] = rec
        elif rec.publish_time == current.publish_time and rec.generation_mw != current.generation_mw:
            raise ConflictingForecastError(
                f"conflicting values for start={rec.start_time.isoformat()} publish={rec.publish_time.isoformat()}"
            )
    return chosen
