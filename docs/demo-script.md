# Video script (target 9:30 total)

Record one continuous screen capture with two chapters. Speak in your own words; these are beats, not lines.

## Part 1: customer pilot review (≤ 4:45)

**0:00 The question (30 s).** "Every morning your desk buys tomorrow's power before the EPEX auction closes at 09:20. Wind is the biggest unknown. This pilot shows exactly which wind forecast you could have acted on, and how far it tended to be wrong, for every January decision."

**0:30 Decision replay (90 s).** Open View 1 on 10 January. Point out: decision date and delivery date are different days; the cutoff; the run used (07:30) and its age at cutoff; coverage 24/24; forecast energy for the day. Hover the chart: each point shows when it was published. Switch to N2EX 09:50: the run changes to 09:30. "Nothing on this screen was unknowable at the time. Actuals are hidden on purpose."

**2:00 Accuracy review (90 s).** Click Review performance. Same day, now with actuals. Explain the sign: red bars are hours where wind was over-forecast and you would have been short. Then "Whole of January": the tiles. MAE about 2,000 MW; bias +1,750 MW, so the forecast systematically over-estimated wind in January; P90 about 4,100 MW as a planning margin. Coverage 744/744.

**3:30 The concrete miss (45 s).** Click the 27 January row. Every hour over-forecast, MAE over 5 GW. "A desk that bought against this forecast was roughly 5 GW short for the whole of 28 January. That is the kind of day a quantified error margin exists for."

**4:15 Limits and next (30 s).** Historical replay only; transmission-metered wind; cutoff is an assumption you can change. Next: your own demand and portfolio, a rolling margin that only uses past data, and alerting on forecast revisions.

## Part 2: technical review (≤ 4:45)

**4:45 Architecture (45 s).** Show `docs/architecture.md` diagram. Ingestion is a script, not a runtime dependency; raw JSON with SHA-256 manifest; immutable read-only SQLite; FastAPI; React. Snapshot id is on every screen and every CSV row.

**5:30 The invariant (75 s).** Open `selection.py`: `select_latest` and the SQL in `db.py`. Open `test_api.py` fixture: the 15:30 run is perfectly accurate and must never be chosen. Run `pytest` live.

**6:45 Alignment and metrics (45 s).** `metrics.py`: hourly mean of two half-hours, both required, no interpolation. Pooled errors, P90 by linear interpolation. `coverage_report.py` output: the same numbers the UI shows.

**7:30 API and frontend (60 s).** `/docs` OpenAPI; `schemas.py`. Frontend: URL is the state (`urlState.ts`), TanStack Query, charts always have a table twin, Europe/London formatting tests.

**8:30 Engineering practice (45 s).** CI workflow: ruff, pytest, eslint, tsc, vitest, build, snapshot rebuild, Docker smoke. `docker compose up`. Vercel single project. Commit history. AI usage disclosed in README.

**9:15 Known gaps (15 s).** No rolling predictive interval; no demand side; snapshot is January only; Vercel runs the function not the image.

## Before uploading

- Unlisted, processing finished, audio audible.
- Open the video, the app URL and the repo in an incognito window.
