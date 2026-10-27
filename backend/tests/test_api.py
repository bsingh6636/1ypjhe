import csv
import io
import math

import pytest

from backend.tests.conftest import ACTUAL_MEAN, DECISION, MISSING_ACTUAL_HOUR, MISSING_FORECAST_HOUR


def test_healthz_reports_snapshot(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert r.json()["snapshot_id"]


def test_metadata_contract(client):
    m = client.get("/api/v1/metadata").json()
    assert m["decision_date_min"] == "2026-01-09"
    assert m["decision_date_max"] == "2026-01-11"
    assert m["default_cutoff"] == "09:20"
    assert {p["key"] for p in m["cutoff_presets"]} == {"epex", "n2ex"}
    assert m["forecast_rows"] > 0 and m["actual_rows"] == 47


def test_replay_selects_only_runs_published_by_cutoff(client):
    r = client.get("/api/v1/forecast", params={"decision_date": DECISION, "cutoff": "09:20"})
    assert r.status_code == 200
    body = r.json()
    assert body["delivery_date"] == "2026-01-11"
    assert body["cutoff_utc"] == "2026-01-10T09:20:00Z"
    assert body["runs_used"] == ["2026-01-09T22:30:00Z", "2026-01-10T07:30:00Z"]
    assert body["coverage"] == {"expected": 24, "covered": 23, "missing": 1}
    pts = {p["start_time"]: p for p in body["points"]}
    assert pts["2026-01-11T00:00:00Z"]["publish_time"] == "2026-01-09T22:30:00Z"  # previous-day fallback
    assert pts["2026-01-11T01:00:00Z"]["forecast_mw"] == ACTUAL_MEAN[1] + 200  # the 07:30 run, not 09:30
    assert pts["2026-01-11T01:00:00Z"]["age_minutes"] == 110
    assert pts["2026-01-11T01:00:00Z"]["lead_hours"] == 17.5
    gap = pts[f"2026-01-11T{MISSING_FORECAST_HOUR:02d}:00:00Z"]
    assert gap["forecast_mw"] is None and gap["publish_time"] is None
    # the replay view never carries actuals
    assert "actual_mw" not in body["points"][0]


def test_replay_later_cutoff_uses_later_run(client):
    body = client.get("/api/v1/forecast", params={"decision_date": DECISION, "cutoff": "n2ex"}).json()
    pts = {p["start_time"]: p for p in body["points"]}
    assert pts["2026-01-11T01:00:00Z"]["forecast_mw"] == ACTUAL_MEAN[1] + 100
    assert pts["2026-01-11T23:00:00Z"]["publish_time"] == "2026-01-10T07:30:00Z"  # 09:30 run misses hour 23


def test_accuracy_hand_checked_summary_and_exclusions(client):
    body = client.get(
        "/api/v1/accuracy", params={"decision_from": DECISION, "decision_to": DECISION, "cutoff": "09:20"}
    ).json()
    s = body["summary"]
    # 24 hours; excluded: the hour with no forecast and the hour with an incomplete actual
    assert s["expected"] == 24 and s["excluded"] == 2 and s["n"] == 22
    # hour 0 comes from the previous-day run (+300); 21 other matched hours from the 07:30 run (+200)
    expected_errors = [300.0] + [200.0] * 21
    assert s["mae_mw"] == pytest.approx(sum(expected_errors) / 22, abs=0.05)
    assert s["bias_mw"] == pytest.approx(sum(expected_errors) / 22, abs=0.05)
    assert s["rmse_mw"] == pytest.approx(math.sqrt(sum(e * e for e in expected_errors) / 22), abs=0.05)
    assert s["p90_abs_mw"] == pytest.approx(200.0, abs=0.05)
    reasons = {r["start_time"]: r["excluded_reason"] for r in body["intervals"] if r["excluded_reason"]}
    assert reasons[f"2026-01-11T{MISSING_FORECAST_HOUR:02d}:00:00Z"] == "no forecast published by cutoff"
    assert reasons[f"2026-01-11T{MISSING_ACTUAL_HOUR:02d}:00:00Z"] == "actual half-hours incomplete"
    assert len(body["daily"]) == 1 and body["daily"][0]["metrics"]["n"] == 22
    assert body["comparison"] is None


def test_accuracy_daily_metrics_pool_errors_not_daily_averages(client):
    body = client.get(
        "/api/v1/accuracy", params={"decision_from": "2026-01-09", "decision_to": DECISION, "cutoff": "09:20"}
    ).json()
    # 2026-01-09 has no forecasts or actuals in the fixture: it must show as fully excluded, not as zero error
    d9 = body["daily"][0]["metrics"]
    assert d9["n"] == 0 and d9["excluded"] == 24 and d9["mae_mw"] is None and d9["reason"]
    assert body["summary"]["expected"] == 48 and body["summary"]["n"] == 22


def test_comparison_uses_identical_matched_cohort(client):
    body = client.get(
        "/api/v1/accuracy",
        params={"decision_from": DECISION, "decision_to": DECISION, "cutoff": "09:20", "compare_cutoff": "09:50"},
    ).json()
    c = body["comparison"]
    # hour 0 (prev-day run on both sides) + hours 1..23 minus hour 22 (no forecast), hour 5 (actual), hour 23
    # is still matched (09:50 side falls back to the 07:30 run there). Both sides: 22 hours.
    assert c["matched_hours"] == 22
    assert c["a"]["metrics"]["n"] == c["b"]["metrics"]["n"] == 22
    assert c["a"]["cutoff"] == "09:20" and c["b"]["cutoff"] == "09:50"
    assert c["b"]["metrics"]["mae_mw"] < c["a"]["metrics"]["mae_mw"]
    assert c["hours_with_different_forecast"] == 20  # hours 1..21 except 5 -> 20 hours differ by 100 MW
    assert c["mean_abs_forecast_change_mw"] == pytest.approx(100 * 20 / 22, abs=0.05)


def test_export_reproduces_summary_metrics(client):
    params = {"decision_from": DECISION, "decision_to": DECISION, "cutoff": "09:20"}
    summary = client.get("/api/v1/accuracy", params=params).json()["summary"]
    r = client.get("/api/v1/export.csv", params=params)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers["content-disposition"]
    rows = list(csv.DictReader(io.StringIO(r.text)))
    assert len(rows) == 24
    errors = [float(x["error_mw"]) for x in rows if x["error_mw"] != ""]
    assert len(errors) == summary["n"]
    assert sum(abs(e) for e in errors) / len(errors) == pytest.approx(summary["mae_mw"], abs=0.05)
    assert all(x["snapshot_id"] == rows[0]["snapshot_id"] and x["cutoff_local"] == "09:20" for x in rows)


@pytest.mark.parametrize(
    "path,params,status",
    [
        ("/api/v1/forecast", {"decision_date": "2026-01-10", "cutoff": "9:20"}, 422),
        ("/api/v1/forecast", {"decision_date": "2026-01-10", "cutoff": "25:00"}, 422),
        ("/api/v1/forecast", {"decision_date": "2026-02-10"}, 422),  # outside snapshot coverage
        ("/api/v1/forecast", {"decision_date": "not-a-date"}, 422),
        ("/api/v1/accuracy", {"decision_from": "2026-01-11", "decision_to": "2026-01-10"}, 422),
        ("/api/v1/accuracy", {"decision_from": "2026-01-10"}, 422),
    ],
)
def test_input_validation(client, path, params, status):
    assert client.get(path, params=params).status_code == status
