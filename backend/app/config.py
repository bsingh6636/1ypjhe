from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Market presets (UK local time). EPEX SPOT GB day-ahead closes 09:20; Nord Pool N2EX closes 09:50.
CUTOFF_PRESETS: dict[str, time] = {"epex": time(9, 20), "n2ex": time(9, 50)}
DEFAULT_CUTOFF = CUTOFF_PRESETS["epex"]
MAX_RANGE_DAYS = 62


@dataclass(frozen=True)
class Settings:
    snapshot_path: Path
    frontend_dist: Path
    timezone: str = "Europe/London"

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            snapshot_path=Path(os.environ.get("SNAPSHOT_PATH", ROOT / "data" / "snapshot.sqlite")),
            frontend_dist=Path(os.environ.get("FRONTEND_DIST", ROOT / "frontend" / "dist")),
        )
