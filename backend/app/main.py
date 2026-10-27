"""FastAPI application. Routes are thin: validate input, open a read-only connection, call services."""

import logging
import re
import sqlite3
import time as _time
import uuid
from collections.abc import Iterator
from datetime import date, datetime, time
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles

from . import db, services
from .config import CUTOFF_PRESETS, DEFAULT_CUTOFF, MAX_RANGE_DAYS, Settings
from .schemas import AccuracyResponse, Health, Metadata, ReplayResponse
from .selection import ConflictingForecastError

log = logging.getLogger("wind_replay")
CUTOFF_RE = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")


def parse_cutoff(value: str) -> time:
    if value in CUTOFF_PRESETS:
        return CUTOFF_PRESETS[value]
    if not CUTOFF_RE.match(value):
        raise HTTPException(status_code=422, detail="cutoff must be HH:MM (UK local time) or a preset key: epex, n2ex")
    return datetime.strptime(value, "%H:%M").time()


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    app = FastAPI(
        title="Wind forecast decision replay",
        version="1.0.0",
        description=(
            "Reconstructs the GB wind generation forecast (Elexon WINDFOR) that was available at a day-ahead "
            "purchase cutoff and evaluates it against metered actuals (Elexon FUELHH, fuelType WIND)."
        ),
    )
    app.state.settings = settings

    def get_conn() -> Iterator[sqlite3.Connection]:
        try:
            conn = db.connect(settings.snapshot_path)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        try:
            yield conn
        finally:
            conn.close()

    Conn = Annotated[sqlite3.Connection, Depends(get_conn)]

    def check_range(conn: sqlite3.Connection, d0: date, d1: date) -> None:
        meta = db.get_meta(conn)
        lo, hi = date.fromisoformat(meta["decision_date_min"]), date.fromisoformat(meta["decision_date_max"])
        if d1 < d0:
            raise HTTPException(status_code=422, detail="decision_to must not be before decision_from")
        if (d1 - d0).days + 1 > MAX_RANGE_DAYS:
            raise HTTPException(status_code=422, detail=f"range exceeds {MAX_RANGE_DAYS} days")
        if d0 < lo or d1 > hi:
            raise HTTPException(
                status_code=422, detail=f"decision dates must be within {lo} to {hi} (snapshot coverage)"
            )

    @app.middleware("http")
    async def request_log(request: Request, call_next):
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
        t0 = _time.perf_counter()
        response = await call_next(request)
        ms = (_time.perf_counter() - t0) * 1000
        response.headers["x-request-id"] = rid
        if request.url.path.startswith("/api") or request.url.path == "/healthz":
            log.info("rid=%s %s %s -> %s %.1fms", rid, request.method, request.url.path, response.status_code, ms)
        return response

    @app.get("/healthz", response_model=Health, tags=["ops"])
    def healthz() -> Health:
        try:
            conn = db.connect(settings.snapshot_path)
            try:
                sid = db.get_meta(conn).get("snapshot_id")
            finally:
                conn.close()
            return Health(status="ok", snapshot_id=sid)
        except Exception as exc:  # readiness must report, not raise
            return Health(status="degraded", snapshot_id=None, detail=str(exc))

    @app.get("/api/v1/metadata", response_model=Metadata, tags=["data"])
    def metadata(conn: Conn) -> Metadata:
        return services.metadata(conn, settings.timezone)

    @app.get("/api/v1/forecast", response_model=ReplayResponse, tags=["replay"])
    def forecast(
        conn: Conn,
        decision_date: Annotated[date, Query(description="Decision date (UK). Delivery is the following day.")],
        cutoff: Annotated[
            str, Query(description="HH:MM UK local time, or preset: epex, n2ex")
        ] = DEFAULT_CUTOFF.strftime("%H:%M"),
    ) -> ReplayResponse:
        check_range(conn, decision_date, decision_date)
        try:
            return services.replay(conn, decision_date, parse_cutoff(cutoff), settings.timezone)
        except ConflictingForecastError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    def _accuracy(conn: sqlite3.Connection, d0: date, d1: date, cutoff: str, compare: str | None) -> AccuracyResponse:
        check_range(conn, d0, d1)
        try:
            return services.accuracy(
                conn,
                d0,
                d1,
                parse_cutoff(cutoff),
                settings.timezone,
                compare_cutoff=parse_cutoff(compare) if compare else None,
            )
        except ConflictingForecastError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.get("/api/v1/accuracy", response_model=AccuracyResponse, tags=["accuracy"])
    def accuracy(
        conn: Conn,
        decision_from: Annotated[date, Query()],
        decision_to: Annotated[date, Query()],
        cutoff: Annotated[str, Query()] = DEFAULT_CUTOFF.strftime("%H:%M"),
        compare_cutoff: Annotated[
            str | None, Query(description="Optional second cutoff for a paired comparison")
        ] = None,
    ) -> AccuracyResponse:
        return _accuracy(conn, decision_from, decision_to, cutoff, compare_cutoff)

    @app.get("/api/v1/export.csv", response_class=PlainTextResponse, tags=["accuracy"])
    def export(
        conn: Conn,
        decision_from: Annotated[date, Query()],
        decision_to: Annotated[date, Query()],
        cutoff: Annotated[str, Query()] = DEFAULT_CUTOFF.strftime("%H:%M"),
    ) -> PlainTextResponse:
        result = _accuracy(conn, decision_from, decision_to, cutoff, None)
        name = f"wind-eval_{decision_from}_{decision_to}_{result.cutoff.replace(':', '')}_{result.snapshot_id}.csv"
        return PlainTextResponse(
            services.export_csv(result),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{name}"'},
        )

    # Serve the built React app, if present, after all API routes so the API always wins.
    if settings.frontend_dist.is_dir():
        app.mount("/", StaticFiles(directory=str(settings.frontend_dist), html=True), name="frontend")

    return app


app = create_app()
