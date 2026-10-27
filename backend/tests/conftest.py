"""Deterministic fixture snapshot. Nothing here touches the network or the real data file."""

from __future__ import annotations

import sys
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))  # so tests can import scripts.build_snapshot and the app package

from scripts.build_snapshot import write_snapshot  # noqa: E402

from backend.app.config import Settings  # noqa: E402
from backend.app.main import create_app  # noqa: E402

DECISION = "2026-01-10"
DELIVERY = datetime(2026, 1, 11, tzinfo=UTC)


def iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def hour(i: int) -> datetime:
    return DELIVERY + timedelta(hours=i)


# Actual hourly means for delivery day: 1000, 1100, ... (half-hours are mean +/- 50 so the mean is exact)
ACTUAL_MEAN = {i: 1000.0 + 100 * i for i in range(24)}
# The 07:30 run over-forecasts by +200 MW everywhere; the 09:30 run is better (+100), and misses hour 23.
RUN_0730 = datetime(2026, 1, 10, 7, 30, tzinfo=UTC)
RUN_0930 = datetime(2026, 1, 10, 9, 30, tzinfo=UTC)
RUN_PREV = datetime(2026, 1, 9, 22, 30, tzinfo=UTC)  # previous-day run, covers hour 0 only -> fallback case
MISSING_FORECAST_HOUR = 22  # no run at all covers this hour
MISSING_ACTUAL_HOUR = 5  # second half-hour of this hour is absent


def raw_records() -> tuple[list[dict], list[dict]]:
    windfor: list[dict] = []
    for i in range(24):
        if i == MISSING_FORECAST_HOUR:
            continue
        if i != 0:  # hour 0 is only covered by the previous-day run
            windfor.append(
                {"publishTime": iso(RUN_0730), "startTime": iso(hour(i)), "generation": ACTUAL_MEAN[i] + 200}
            )
            if i != 23:
                windfor.append(
                    {"publishTime": iso(RUN_0930), "startTime": iso(hour(i)), "generation": ACTUAL_MEAN[i] + 100}
                )
    windfor.append({"publishTime": iso(RUN_PREV), "startTime": iso(hour(0)), "generation": ACTUAL_MEAN[0] + 300})
    # a tempting but ineligible later run (published after both cutoffs) that is perfectly accurate
    for i in range(1, 24):
        if i != MISSING_FORECAST_HOUR:
            windfor.append(
                {"publishTime": "2026-01-10T15:30:00Z", "startTime": iso(hour(i)), "generation": ACTUAL_MEAN[i]}
            )

    fuelhh: list[dict] = []
    for i in range(24):
        for half, delta in ((0, -50.0), (30, 50.0)):
            if i == MISSING_ACTUAL_HOUR and half == 30:
                continue
            t = hour(i) + timedelta(minutes=half)
            fuelhh.append(
                {
                    "fuelType": "WIND",
                    "publishTime": iso(t + timedelta(minutes=30)),
                    "startTime": iso(t),
                    "settlementDate": "2026-01-11",
                    "settlementPeriod": 2 * i + (1 if half == 0 else 2),
                    "generation": ACTUAL_MEAN[i] + delta,
                }
            )
    # a non-wind row that must be ignored
    fuelhh.append(
        {
            "fuelType": "CCGT",
            "publishTime": iso(hour(0)),
            "startTime": iso(hour(0)),
            "settlementDate": "2026-01-11",
            "settlementPeriod": 1,
            "generation": 9999,
        }
    )
    return windfor, fuelhh


@pytest.fixture(scope="session")
def snapshot_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    from scripts.build_snapshot import normalise

    windfor, fuelhh = raw_records()
    forecast, actual, rejected = normalise(windfor, fuelhh)
    out = tmp_path_factory.mktemp("snap") / "snapshot.sqlite"
    manifest = {"files": {"windfor": {"sha256": "a" * 64}, "fuelhh_wind": {"sha256": "b" * 64}}}
    write_snapshot(out, forecast, actual, Counter(rejected), manifest, "2026-01-09", "2026-01-11")
    return out


@pytest.fixture(scope="session")
def client(snapshot_path: Path, tmp_path_factory: pytest.TempPathFactory) -> TestClient:
    settings = Settings(snapshot_path=snapshot_path, frontend_dist=tmp_path_factory.mktemp("nodist") / "missing")
    return TestClient(create_app(settings))
