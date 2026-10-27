"""Orchestration: snapshot rows -> selection -> alignment -> metrics -> response models."""

from __future__ import annotations

import csv
import io
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from . import db
from .config import CUTOFF_PRESETS, DEFAULT_CUTOFF
from .metrics import ErrorMetrics, compute_metrics, energy_mwh, hourly_mean_actual
from .schemas import (
    AccuracyResponse,
    Comparison,
    ComparisonSide,
    Coverage,
    CutoffPreset,
    DailySummary,
    ForecastPoint,
    IntervalRow,
    Metadata,
    MetricsBlock,
    ReplayResponse,
)
from .selection import ForecastRecord, cutoff_utc, delivery_window, expected_hours, select_latest

PRESET_LABELS = {"epex": "EPEX SPOT GB day-ahead (09:20)", "n2ex": "Nord Pool N2EX day-ahead (09:50)"}


def fmt_cutoff(t: time) -> str:
    return t.strftime("%H:%M")


@dataclass(frozen=True)
class EvaluatedHour:
    start_time: datetime
    forecast: ForecastRecord | None
    actual_mw: float | None

    @property
    def error_mw(self) -> float | None:
        if self.forecast is None or self.actual_mw is None:
            return None
        return self.forecast.generation_mw - self.actual_mw

    @property
    def excluded_reason(self) -> str | None:
        if self.forecast is None and self.actual_mw is None:
            return "no eligible forecast; actual incomplete"
        if self.forecast is None:
            return "no forecast published by cutoff"
        if self.actual_mw is None:
            return "actual half-hours incomplete"
        return None


@dataclass(frozen=True)
class DayEvaluation:
    decision_date: date
    delivery_date: date
    cutoff_utc: datetime
    hours: list[EvaluatedHour]

    @property
    def runs_used(self) -> list[str]:
        return sorted({db.to_iso(h.forecast.publish_time) for h in self.hours if h.forecast is not None})

    @property
    def errors(self) -> list[float]:
        return [h.error_mw for h in self.hours if h.error_mw is not None]


def _evaluate_day(
    conn: sqlite3.Connection, decision_date: date, cutoff: time, tz: str, with_actuals: bool
) -> DayEvaluation:
    cut = cutoff_utc(decision_date, cutoff, tz)
    start, end = delivery_window(decision_date, tz)
    hours = expected_hours(start, end)
    chosen = select_latest(db.forecast_candidates(conn, start, end, cut), cut)
    actuals = db.actuals_between(conn, start, end) if with_actuals else {}
    evaluated = [
        EvaluatedHour(h, chosen.get(h), hourly_mean_actual(h, actuals) if with_actuals else None) for h in hours
    ]
    return DayEvaluation(decision_date, decision_date + timedelta(days=1), cut, evaluated)


def _metrics_block(hours: list[EvaluatedHour]) -> MetricsBlock:
    matched = [h for h in hours if h.error_mw is not None]
    m: ErrorMetrics | None = compute_metrics([h.error_mw for h in matched])  # type: ignore[misc]
    expected = len(hours)
    if m is None:
        return MetricsBlock(
            n=0,
            expected=expected,
            excluded=expected,
            mae_mw=None,
            rmse_mw=None,
            bias_mw=None,
            p90_abs_mw=None,
            forecast_mwh=None,
            actual_mwh=None,
            reason="no matched intervals",
        )
    return MetricsBlock(
        n=m.n,
        expected=expected,
        excluded=expected - m.n,
        mae_mw=round(m.mae_mw, 1),
        rmse_mw=round(m.rmse_mw, 1),
        bias_mw=round(m.bias_mw, 1),
        p90_abs_mw=round(m.p90_abs_mw, 1),
        forecast_mwh=round(energy_mwh([h.forecast.generation_mw for h in matched], 1.0), 1),  # type: ignore[union-attr]
        actual_mwh=round(energy_mwh([h.actual_mw for h in matched], 1.0), 1),  # type: ignore[misc]
    )


def metadata(conn: sqlite3.Connection, tz: str) -> Metadata:
    meta = db.get_meta(conn)
    return Metadata(
        snapshot_id=meta["snapshot_id"],
        built_at_utc=meta["built_at_utc"],
        decision_date_min=date.fromisoformat(meta["decision_date_min"]),
        decision_date_max=date.fromisoformat(meta["decision_date_max"]),
        timezone=tz,
        units=meta.get("units", "MW"),
        methodology_version=meta.get("methodology_version", "1.0"),
        forecast_rows=int(meta["forecast_rows"]),
        forecast_runs=int(meta["forecast_runs"]),
        actual_rows=int(meta["actual_rows"]),
        cutoff_presets=[
            CutoffPreset(key=k, label=PRESET_LABELS[k], time=fmt_cutoff(t)) for k, t in CUTOFF_PRESETS.items()
        ],
        default_cutoff=fmt_cutoff(DEFAULT_CUTOFF),
        source=db.source_manifest(conn),
    )


def replay(conn: sqlite3.Connection, decision_date: date, cutoff: time, tz: str) -> ReplayResponse:
    """View 1: what was knowable at the cutoff. Actuals are deliberately not loaded here."""
    day = _evaluate_day(conn, decision_date, cutoff, tz, with_actuals=False)
    meta = db.get_meta(conn)
    points = []
    for h in day.hours:
        f = h.forecast
        points.append(
            ForecastPoint(
                start_time=db.to_iso(h.start_time),
                forecast_mw=f.generation_mw if f else None,
                publish_time=db.to_iso(f.publish_time) if f else None,
                age_minutes=int((day.cutoff_utc - f.publish_time).total_seconds() // 60) if f else None,
                lead_hours=round((h.start_time - f.publish_time).total_seconds() / 3600, 1) if f else None,
            )
        )
    covered = [h.forecast.generation_mw for h in day.hours if h.forecast is not None]
    return ReplayResponse(
        decision_date=decision_date,
        delivery_date=day.delivery_date,
        cutoff=fmt_cutoff(cutoff),
        cutoff_utc=db.to_iso(day.cutoff_utc),
        timezone=tz,
        snapshot_id=meta["snapshot_id"],
        runs_used=day.runs_used,
        coverage=Coverage(expected=len(day.hours), covered=len(covered), missing=len(day.hours) - len(covered)),
        points=points,
        forecast_mwh=round(energy_mwh(covered, 1.0), 1) if covered else None,
    )


def _date_range(d0: date, d1: date) -> list[date]:
    return [d0 + timedelta(days=i) for i in range((d1 - d0).days + 1)]


def accuracy(
    conn: sqlite3.Connection,
    decision_from: date,
    decision_to: date,
    cutoff: time,
    tz: str,
    compare_cutoff: time | None = None,
) -> AccuracyResponse:
    """View 2: retrospective evaluation of the cutoff-eligible forecasts against actuals."""
    meta = db.get_meta(conn)
    days = [_evaluate_day(conn, d, cutoff, tz, with_actuals=True) for d in _date_range(decision_from, decision_to)]
    all_hours = [h for d in days for h in d.hours]
    daily = [
        DailySummary(
            decision_date=d.decision_date,
            delivery_date=d.delivery_date,
            cutoff_utc=db.to_iso(d.cutoff_utc),
            runs_used=d.runs_used,
            metrics=_metrics_block(d.hours),
        )
        for d in days
    ]
    intervals = [
        IntervalRow(
            decision_date=d.decision_date,
            start_time=db.to_iso(h.start_time),
            forecast_mw=h.forecast.generation_mw if h.forecast else None,
            actual_mw=round(h.actual_mw, 1) if h.actual_mw is not None else None,
            error_mw=round(h.error_mw, 1) if h.error_mw is not None else None,
            publish_time=db.to_iso(h.forecast.publish_time) if h.forecast else None,
            excluded_reason=h.excluded_reason,
        )
        for d in days
        for h in d.hours
    ]
    comparison = None
    if compare_cutoff is not None and compare_cutoff != cutoff:
        comparison = _compare(conn, days, decision_from, decision_to, cutoff, compare_cutoff, tz)
    return AccuracyResponse(
        decision_from=decision_from,
        decision_to=decision_to,
        cutoff=fmt_cutoff(cutoff),
        timezone=tz,
        snapshot_id=meta["snapshot_id"],
        summary=_metrics_block(all_hours),
        daily=daily,
        intervals=intervals,
        comparison=comparison,
    )


def _compare(
    conn: sqlite3.Connection,
    days_a: list[DayEvaluation],
    d0: date,
    d1: date,
    cutoff_a: time,
    cutoff_b: time,
    tz: str,
) -> Comparison:
    """Paired comparison on the intersection of hours where BOTH cutoffs have a forecast and a complete actual."""
    days_b = [_evaluate_day(conn, d, cutoff_b, tz, with_actuals=True) for d in _date_range(d0, d1)]
    by_time_b = {h.start_time: h for d in days_b for h in d.hours}
    pairs: list[tuple[EvaluatedHour, EvaluatedHour]] = []
    for d in days_a:
        for ha in d.hours:
            hb = by_time_b.get(ha.start_time)
            if hb is not None and ha.error_mw is not None and hb.error_mw is not None:
                pairs.append((ha, hb))
    a_hours = [p[0] for p in pairs]
    b_hours = [p[1] for p in pairs]
    changes = [abs(pb.forecast.generation_mw - pa.forecast.generation_mw) for pa, pb in pairs]  # type: ignore[union-attr]
    different = sum(1 for c in changes if c != 0)
    return Comparison(
        note="Both sides evaluated on the identical matched hours; coverage differences are excluded, not averaged.",
        matched_hours=len(pairs),
        hours_with_different_forecast=different,
        mean_abs_forecast_change_mw=round(sum(changes) / len(changes), 1) if changes else None,
        a=ComparisonSide(
            cutoff=fmt_cutoff(cutoff_a),
            metrics=_metrics_block(a_hours),
            runs_used=sorted({db.to_iso(h.forecast.publish_time) for h in a_hours}),  # type: ignore[union-attr]
        ),
        b=ComparisonSide(
            cutoff=fmt_cutoff(cutoff_b),
            metrics=_metrics_block(b_hours),
            runs_used=sorted({db.to_iso(h.forecast.publish_time) for h in b_hours}),  # type: ignore[union-attr]
        ),
    )


EXPORT_COLUMNS = [
    "snapshot_id",
    "timezone",
    "cutoff_local",
    "decision_date",
    "delivery_hour_start_utc",
    "forecast_mw",
    "forecast_publish_time_utc",
    "actual_hourly_mean_mw",
    "error_mw",
    "excluded_reason",
]


def export_csv(result: AccuracyResponse) -> str:
    """Flat CSV of the evaluated selection. Metrics are reproducible from the error_mw column."""
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(EXPORT_COLUMNS)
    for r in result.intervals:
        w.writerow(
            [
                result.snapshot_id,
                result.timezone,
                result.cutoff,
                r.decision_date.isoformat(),
                r.start_time,
                r.forecast_mw,
                r.publish_time,
                r.actual_mw,
                r.error_mw,
                r.excluded_reason or "",
            ]
        )
    return buf.getvalue()
