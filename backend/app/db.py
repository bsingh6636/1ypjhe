"""Read-only access to the immutable SQLite snapshot. One connection per request, parameterised SQL only."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from .selection import ForecastRecord


def to_iso(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def from_iso(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(UTC)


def connect(path: Path) -> sqlite3.Connection:
    if not path.exists():
        raise FileNotFoundError(f"snapshot not found: {path}")
    uri = f"{path.resolve().as_uri()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def get_meta(conn: sqlite3.Connection) -> dict[str, str]:
    return {row["key"]: row["value"] for row in conn.execute("SELECT key, value FROM meta")}


def source_manifest(conn: sqlite3.Connection) -> dict:
    raw = get_meta(conn).get("source_manifest", "{}")
    return json.loads(raw)


def forecast_candidates(
    conn: sqlite3.Connection, start_from: datetime, start_to: datetime, published_by: datetime
) -> list[ForecastRecord]:
    """All forecast records for start_time in [start_from, start_to) published at or before `published_by`.

    The look-ahead guard lives in SQL *and* in selection.select_latest, so a bug in one cannot leak future data.
    """
    rows = conn.execute(
        "SELECT publish_time, start_time, generation_mw FROM forecast "
        "WHERE start_time >= ? AND start_time < ? AND publish_time <= ? "
        "ORDER BY start_time, publish_time",
        (to_iso(start_from), to_iso(start_to), to_iso(published_by)),
    )
    return [
        ForecastRecord(from_iso(r["publish_time"]), from_iso(r["start_time"]), float(r["generation_mw"])) for r in rows
    ]


def actuals_between(conn: sqlite3.Connection, start_from: datetime, start_to: datetime) -> dict[datetime, float]:
    rows = conn.execute(
        "SELECT start_time, generation_mw FROM actual WHERE start_time >= ? AND start_time < ? ORDER BY start_time",
        (to_iso(start_from), to_iso(start_to)),
    )
    return {from_iso(r["start_time"]): float(r["generation_mw"]) for r in rows}
