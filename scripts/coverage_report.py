"""Coverage and headline accuracy per decision date, computed through the same code path as the API.

Use it to validate a snapshot before shipping it, and to quote real numbers in the README/demo.

Usage: python scripts/coverage_report.py [--snapshot data/snapshot.sqlite] [--cutoff 09:20] [--compare 09:50]
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app import db, services  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--snapshot", default=str(ROOT / "data" / "snapshot.sqlite"))
    ap.add_argument("--cutoff", default="09:20")
    ap.add_argument("--compare", default=None)
    args = ap.parse_args(argv)

    conn = db.connect(Path(args.snapshot))
    meta = db.get_meta(conn)
    d0, d1 = date.fromisoformat(meta["decision_date_min"]), date.fromisoformat(meta["decision_date_max"])
    cutoff = datetime.strptime(args.cutoff, "%H:%M").time()
    compare = datetime.strptime(args.compare, "%H:%M").time() if args.compare else None
    res = services.accuracy(conn, d0, d1, cutoff, meta["timezone"], compare_cutoff=compare)

    print(f"snapshot {meta['snapshot_id']}  decisions {d0}..{d1}  cutoff {args.cutoff} UK")
    print(
        f"{'decision':<11}{'delivery':<11}{'runs':<8}{'matched':>8}{'excl':>5}{'MAE':>8}{'RMSE':>8}{'bias':>8}{'P90':>8}"
    )
    bad = 0
    for d in res.daily:
        m = d.metrics
        if m.excluded:
            bad += 1
        clocks = ",".join(sorted({r[11:16] for r in d.runs_used}))
        print(
            f"{d.decision_date!s:<11}{d.delivery_date!s:<11}{clocks:<8}{m.n:>5}/{m.expected:<2}{m.excluded:>5}"
            f"{m.mae_mw or 0:>8.0f}{m.rmse_mw or 0:>8.0f}{m.bias_mw or 0:>+8.0f}{m.p90_abs_mw or 0:>8.0f}"
        )
    s = res.summary
    print(
        f"\nTOTAL matched {s.n}/{s.expected} (excluded {s.excluded})  MAE {s.mae_mw:.0f}  RMSE {s.rmse_mw:.0f}  "
        f"bias {s.bias_mw:+.0f}  P90 {s.p90_abs_mw:.0f} MW"
    )
    if res.comparison:
        c = res.comparison
        for side in (c.a, c.b):
            m = side.metrics
            print(
                f"compare {side.cutoff}: n={m.n} MAE {m.mae_mw:.0f} RMSE {m.rmse_mw:.0f} bias {m.bias_mw:+.0f} "
                f"P90 {m.p90_abs_mw:.0f}"
            )
        print(f"paired hours {c.matched_hours}, forecast differed in {c.hours_with_different_forecast}")
    print(f"days with exclusions: {bad}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
