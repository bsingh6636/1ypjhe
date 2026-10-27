"""Normalise raw Elexon responses into an immutable, indexed SQLite snapshot.

Validation performed here, so the API never has to guess:
  * generation must be numeric and non-null
  * identical duplicate records are collapsed; conflicting duplicates abort the build
  * forecast startTimes must be on the hour, actual startTimes on the half hour
  * every settlement day in the actuals must have 48 periods (reported, not fatal)

Usage: python scripts/build_snapshot.py [--raw data/raw] [--out data/snapshot.sqlite]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SCHEMA = """
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE forecast (
    publish_time TEXT NOT NULL,   -- ISO-8601 UTC, e.g. 2026-01-10T07:30:00Z
    start_time   TEXT NOT NULL,   -- ISO-8601 UTC, hourly
    generation_mw REAL NOT NULL,
    PRIMARY KEY (start_time, publish_time)
);
CREATE INDEX ix_forecast_publish ON forecast (publish_time);
CREATE TABLE actual (
    start_time TEXT PRIMARY KEY,  -- ISO-8601 UTC, half-hourly
    settlement_date TEXT NOT NULL,
    settlement_period INTEGER NOT NULL,
    generation_mw REAL NOT NULL,
    publish_time TEXT NOT NULL
);
"""


def iso_utc(s: str) -> str:
    """Canonical ISO form with trailing Z (input is already UTC from Elexon)."""
    dt = datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(UTC)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def normalise(windfor: list[dict], fuelhh: list[dict]) -> tuple[dict, dict, Counter]:
    """Pure transformation used by the build and by tests. Returns (forecast, actual, rejected)."""
    forecast: dict[tuple[str, str], float] = {}
    rejected: Counter = Counter()
    for r in windfor:
        if r.get("generation") is None:
            rejected["forecast_null"] += 1
            continue
        key = (iso_utc(r["startTime"]), iso_utc(r["publishTime"]))
        if not key[0].endswith(":00:00Z"):
            rejected["forecast_not_hourly"] += 1
            continue
        val = float(r["generation"])
        if key in forecast and forecast[key] != val:
            raise ValueError(f"conflicting duplicate forecast {key}: {forecast[key]} vs {val}")
        forecast[key] = val

    actual: dict[str, tuple[str, int, float, str]] = {}
    for r in fuelhh:
        if r.get("fuelType") != "WIND":
            rejected["actual_other_fuel"] += 1
            continue
        if r.get("generation") is None:
            rejected["actual_null"] += 1
            continue
        st = iso_utc(r["startTime"])
        if st[14:16] not in ("00", "30"):
            rejected["actual_not_half_hourly"] += 1
            continue
        row = (r["settlementDate"], int(r["settlementPeriod"]), float(r["generation"]), iso_utc(r["publishTime"]))
        if st in actual and actual[st][2] != row[2]:
            raise ValueError(f"conflicting duplicate actual {st}: {actual[st][2]} vs {row[2]}")
        actual[st] = row
    return forecast, actual, rejected


def write_snapshot(
    out: Path,
    forecast: dict,
    actual: dict,
    rejected: Counter,
    manifest: dict,
    decision_min: str,
    decision_max: str,
) -> dict:
    per_day = Counter(v[0] for v in actual.values())
    incomplete_days = {d: n for d, n in per_day.items() if n != 48}

    if out.exists():
        out.unlink()
    out.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(out)
    conn.executescript(SCHEMA)
    conn.executemany("INSERT INTO forecast VALUES (?,?,?)", [(p, s, g) for (s, p), g in forecast.items()])
    conn.executemany("INSERT INTO actual VALUES (?,?,?,?,?)", [(s, *v) for s, v in actual.items()])

    digest = hashlib.sha256()
    for name in sorted(manifest.get("files", {})):
        digest.update(manifest["files"][name]["sha256"].encode())
    snapshot_id = digest.hexdigest()[:12] if manifest.get("files") else "unmanifested"
    meta = {
        "snapshot_id": snapshot_id,
        "built_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "source_manifest": json.dumps(manifest),
        "forecast_rows": str(len(forecast)),
        "forecast_runs": str(len({p for (_, p) in forecast})),
        "actual_rows": str(len(actual)),
        "incomplete_actual_days": json.dumps(incomplete_days),
        "rejected": json.dumps(rejected),
        "decision_date_min": decision_min,
        "decision_date_max": decision_max,
        "timezone": "Europe/London",
        "units": "MW",
        "methodology_version": "1.0",
    }
    conn.executemany("INSERT INTO meta VALUES (?,?)", list(meta.items()))
    conn.commit()
    conn.execute("VACUUM")
    conn.close()
    return meta


def build(raw_dir: Path, out: Path, decision_min: str = "2026-01-01", decision_max: str = "2026-01-31") -> dict:
    windfor = json.loads((raw_dir / "windfor.json").read_bytes())
    fuelhh = json.loads((raw_dir / "fuelhh_wind.json").read_bytes())
    manifest_path = raw_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    forecast, actual, rejected = normalise(windfor, fuelhh)
    return write_snapshot(out, forecast, actual, rejected, manifest, decision_min, decision_max)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raw", default=str(ROOT / "data" / "raw"))
    ap.add_argument("--out", default=str(ROOT / "data" / "snapshot.sqlite"))
    args = ap.parse_args(argv)
    meta = build(Path(args.raw), Path(args.out))
    for k in ("snapshot_id", "forecast_rows", "forecast_runs", "actual_rows", "incomplete_actual_days", "rejected"):
        print(f"{k}: {meta[k]}")
    print(f"snapshot -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
