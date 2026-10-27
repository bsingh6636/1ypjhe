"""API response contracts (Pydantic v2). Times are ISO-8601 UTC strings ending in Z."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class CutoffPreset(BaseModel):
    key: str
    label: str
    time: str = Field(description="HH:MM UK local time")


class Metadata(BaseModel):
    snapshot_id: str
    built_at_utc: str
    decision_date_min: date
    decision_date_max: date
    timezone: str
    units: str
    methodology_version: str
    forecast_rows: int
    forecast_runs: int
    actual_rows: int
    cutoff_presets: list[CutoffPreset]
    default_cutoff: str
    source: dict


class ForecastPoint(BaseModel):
    start_time: str
    forecast_mw: float | None
    publish_time: str | None
    age_minutes: int | None = Field(description="Minutes between publication and the decision cutoff")
    lead_hours: float | None = Field(description="Hours between publication and the start of the delivery hour")


class Coverage(BaseModel):
    expected: int
    covered: int
    missing: int


class ReplayResponse(BaseModel):
    decision_date: date
    delivery_date: date
    cutoff: str
    cutoff_utc: str
    timezone: str
    snapshot_id: str
    runs_used: list[str] = Field(description="Distinct forecast publication times that contributed points")
    coverage: Coverage
    points: list[ForecastPoint]
    forecast_mwh: float | None = Field(description="Sum of covered hourly forecasts x 1h; null if no coverage")


class MetricsBlock(BaseModel):
    n: int
    expected: int
    excluded: int
    mae_mw: float | None
    rmse_mw: float | None
    bias_mw: float | None
    p90_abs_mw: float | None
    forecast_mwh: float | None
    actual_mwh: float | None
    reason: str | None = None


class DailySummary(BaseModel):
    decision_date: date
    delivery_date: date
    cutoff_utc: str
    runs_used: list[str]
    metrics: MetricsBlock


class IntervalRow(BaseModel):
    decision_date: date
    start_time: str
    forecast_mw: float | None
    actual_mw: float | None
    error_mw: float | None
    publish_time: str | None
    excluded_reason: str | None = None


class ComparisonSide(BaseModel):
    cutoff: str
    metrics: MetricsBlock
    runs_used: list[str]


class Comparison(BaseModel):
    note: str
    matched_hours: int
    hours_with_different_forecast: int
    mean_abs_forecast_change_mw: float | None
    a: ComparisonSide
    b: ComparisonSide


class AccuracyResponse(BaseModel):
    decision_from: date
    decision_to: date
    cutoff: str
    timezone: str
    snapshot_id: str
    summary: MetricsBlock
    daily: list[DailySummary]
    intervals: list[IntervalRow]
    comparison: Comparison | None = None


class Health(BaseModel):
    status: str
    snapshot_id: str | None
    detail: str | None = None
