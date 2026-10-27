"""Fetch WINDFOR forecast vintages and FUELHH WIND actuals from the public Elexon Insights API.

Writes raw responses to data/raw/ unchanged, plus a manifest with URL, fetch time,
byte count and SHA-256 so the snapshot can be traced back to its source.

Usage:
    python scripts/fetch_elexon.py [--publish-from 2025-12-30T00:00Z] [--publish-to 2026-02-02T00:00Z]
                                   [--settlement-from 2026-01-01] [--settlement-to 2026-02-01]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

BASE = "https://data.elexon.co.uk/bmrs/api/v1/datasets"
ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"


def fetch(url: str, retries: int = 3, timeout: int = 180) -> bytes:
    last: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "wind-forecast-replay/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except (urllib.error.URLError, TimeoutError) as exc:  # bounded retry with backoff
            last = exc
            time.sleep(2**attempt)
    raise RuntimeError(f"failed after {retries} attempts: {url}") from last


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--publish-from", default="2025-12-30T00:00Z")
    ap.add_argument("--publish-to", default="2026-02-02T00:00Z")
    ap.add_argument("--settlement-from", default="2026-01-01")
    ap.add_argument("--settlement-to", default="2026-02-01")
    args = ap.parse_args(argv)

    queries = {
        "windfor": (
            f"{BASE}/WINDFOR/stream?publishDateTimeFrom={args.publish_from}&publishDateTimeTo={args.publish_to}"
        ),
        "fuelhh_wind": (
            f"{BASE}/FUELHH/stream?settlementDateFrom={args.settlement_from}"
            f"&settlementDateTo={args.settlement_to}&fuelType=WIND"
        ),
    }
    RAW.mkdir(parents=True, exist_ok=True)
    files: dict[str, dict[str, object]] = {}
    for name, url in queries.items():
        body = fetch(url)
        rows = json.loads(body)
        path = RAW / f"{name}.json"
        path.write_bytes(body)
        files[name] = {
            "url": url,
            "fetched_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
            "bytes": len(body),
            "sha256": hashlib.sha256(body).hexdigest(),
            "rows": len(rows),
            "file": path.name,
        }
        print(f"{name}: {len(rows)} rows, {len(body)} bytes -> {path}")
    manifest = {"source": "Elexon Insights Solution (BMRS) public API", "files": files}
    (RAW / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"manifest -> {RAW / 'manifest.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
