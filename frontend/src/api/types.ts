// Mirrors backend/app/schemas.py. Times are ISO-8601 UTC strings ending in Z.

export interface CutoffPreset {
  key: string;
  label: string;
  time: string;
}

export interface Metadata {
  snapshot_id: string;
  built_at_utc: string;
  decision_date_min: string;
  decision_date_max: string;
  timezone: string;
  units: string;
  methodology_version: string;
  forecast_rows: number;
  forecast_runs: number;
  actual_rows: number;
  cutoff_presets: CutoffPreset[];
  default_cutoff: string;
  source: { files?: Record<string, { url: string; fetched_at_utc: string; sha256: string; rows: number }> };
}

export interface ForecastPoint {
  start_time: string;
  forecast_mw: number | null;
  publish_time: string | null;
  age_minutes: number | null;
  lead_hours: number | null;
}

export interface Coverage {
  expected: number;
  covered: number;
  missing: number;
}

export interface ReplayResponse {
  decision_date: string;
  delivery_date: string;
  cutoff: string;
  cutoff_utc: string;
  timezone: string;
  snapshot_id: string;
  runs_used: string[];
  coverage: Coverage;
  points: ForecastPoint[];
  forecast_mwh: number | null;
}

export interface MetricsBlock {
  n: number;
  expected: number;
  excluded: number;
  mae_mw: number | null;
  rmse_mw: number | null;
  bias_mw: number | null;
  p90_abs_mw: number | null;
  forecast_mwh: number | null;
  actual_mwh: number | null;
  reason: string | null;
}

export interface DailySummary {
  decision_date: string;
  delivery_date: string;
  cutoff_utc: string;
  runs_used: string[];
  metrics: MetricsBlock;
}

export interface IntervalRow {
  decision_date: string;
  start_time: string;
  forecast_mw: number | null;
  actual_mw: number | null;
  error_mw: number | null;
  publish_time: string | null;
  excluded_reason: string | null;
}

export interface ComparisonSide {
  cutoff: string;
  metrics: MetricsBlock;
  runs_used: string[];
}

export interface Comparison {
  note: string;
  matched_hours: number;
  hours_with_different_forecast: number;
  mean_abs_forecast_change_mw: number | null;
  a: ComparisonSide;
  b: ComparisonSide;
}

export interface AccuracyResponse {
  decision_from: string;
  decision_to: string;
  cutoff: string;
  timezone: string;
  snapshot_id: string;
  summary: MetricsBlock;
  daily: DailySummary[];
  intervals: IntervalRow[];
  comparison: Comparison | null;
}
