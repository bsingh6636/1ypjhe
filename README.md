# Wind forecast decision replay

A pilot web app for a GB utility's day-ahead purchasing desk. It reconstructs the national wind generation forecast that was available at the purchase cutoff for every decision day in January 2026, and quantifies how accurate those forecasts were against metered actuals.

- **Live app:** https://1ypjhe.vercel.app
- **Data:** Elexon Insights API only: `WINDFOR` (forecast vintages) and `FUELHH` with `fuelType=WIND` (actuals). Contains BMRS data © Elexon Limited copyright and database right 2026.
- **Stack:** React 18 + TypeScript + Vite + TanStack Query + Recharts; Python 3.12 + FastAPI + Pydantic; SQLite snapshot; Docker; GitHub Actions; Vercel.

## What it does

**View 1, Decision replay.** Pick a decision date and a cutoff (EPEX GB 09:20 by default, N2EX 09:50, or any time). The app shows, hour by hour for the following delivery day, the latest forecast that had been *published by that cutoff*, with the publication time, age and lead time of every point, the coverage, and the implied wind energy. Actuals are hidden on this view: it shows only what was knowable.

**View 2, Accuracy review.** For a day or a range of decision days, compare those cutoff-eligible forecasts with Elexon actuals: MAE, RMSE, bias, P90 absolute error, coverage and exclusions, a forecast-vs-actual chart, a signed error chart, a daily table with drill-down, a paired comparison of two cutoffs on identical hours, and a CSV export that reproduces the metrics.

January 2026 result at the 09:20 cutoff: 744 of 744 hours matched, MAE 2,039 MW, bias +1,748 MW (wind was over-forecast on average), P90 absolute error 4,098 MW. Details and definitions are in [docs/methodology.md](docs/methodology.md).

## Repository layout

```
backend/
  app/
    main.py          FastAPI routes, validation, request logging, static mount
    services.py      per-day evaluation, aggregation, comparison, CSV export
    selection.py     pure: cutoff instant, delivery window, latest-eligible-run selection
    metrics.py       pure: hourly alignment rule, MAE/RMSE/bias/P90, MWh
    db.py            read-only SQLite access, parameterised SQL
    schemas.py       Pydantic response contracts
    config.py        settings and cutoff presets
  tests/             pytest: selection, metrics, API (synthetic snapshot fixture)
  requirements*.txt  runtime and dev dependencies
frontend/
  src/
    App.tsx                 tabs, header, metadata
    features/ReplayView.tsx View 1
    features/AccuracyView.tsx View 2 and comparison panel
    components/             charts, tables, cutoff picker, metric tiles, banners, methodology
    state/urlState.ts       selection state lives in the URL
    api/                    typed client and TanStack Query hooks
    lib/format.ts           Europe/London formatting
    *.test.ts(x)            vitest + Testing Library
scripts/
  fetch_elexon.py      download raw WINDFOR / FUELHH with a SHA-256 manifest
  build_snapshot.py    validate and normalise raw JSON into data/snapshot.sqlite
  coverage_report.py   per-day coverage and metrics through the API code path
data/
  raw/                 raw API responses + manifest.json (as fetched 27 Oct 2026)
  snapshot.sqlite      immutable snapshot the app serves (built from data/raw)
docs/
  methodology.md       definitions, alignment rule, metrics, limits, January headline
  architecture.md      components, API, deployment, tests
  demo-script.md       outline for the two-part video
.github/workflows/ci.yml   lint, tests, build, snapshot rebuild, Docker smoke test
Dockerfile, compose.yaml   multi-stage image; one-command local run
vercel.json, pyproject.toml Vercel single-project deployment config
```

## Run it

### Docker (recommended)

```bash
docker compose up --build
# open http://localhost:8000
```

### Local development

Backend (Python 3.12+):

```bash
python -m venv .venv && . .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r backend/requirements-dev.txt
uvicorn backend.app.main:app --reload --port 8000  # API at /api/v1, OpenAPI at /docs
```

Frontend (Node 20+), in a second terminal:

```bash
cd frontend
npm ci
npm run dev        # http://localhost:5173, proxies /api to :8000
```

### Tests and checks

```bash
ruff check backend scripts && ruff format --check backend scripts
pytest                                   # 31 backend tests
cd frontend && npm run lint && npm run typecheck && npm test && npm run build
python scripts/coverage_report.py --compare 09:50   # real-snapshot validation
```

### Rebuild the data snapshot

```bash
python scripts/fetch_elexon.py     # fetches WINDFOR (publish 30 Dec 2025 to 2 Feb 2026) and FUELHH WIND (1 Jan to 1 Feb 2026)
python scripts/build_snapshot.py   # writes data/snapshot.sqlite with a snapshot id derived from the raw SHA-256s
```

The committed snapshot is `e9a00d8a41e0`. The API never calls Elexon at runtime.

## Deployment

- **Vercel:** import the repo as one project. `pyproject.toml` declares the FastAPI entrypoint; `vercel.json` builds the Vite app first and FastAPI mounts `frontend/dist`, so one function serves both the API and the SPA. Vercel runs the Python function, not the Docker image.
- **Heroku (container stack):** `heroku container:push web && heroku container:release web`. The image honours `$PORT`.

## Key assumptions

- "Purchase decisions in January 2026" means decision dates 1 to 31 January, delivering 2 January to 1 February. Each decision covers the whole following UK calendar day.
- The default cutoff of 09:20 UK is the EPEX SPOT GB day-ahead gate closure; 09:50 is Nord Pool N2EX. The client's actual exchange and internal deadline are unknown, so the cutoff is editable and always displayed.
- Hourly forecasts are compared with the mean of the two half-hour actuals in that hour; an hour with a missing half-hour or no eligible forecast is excluded and counted, never filled.
- Error = forecast − actual. Positive means over-forecast, which leaves a buyer short.
- The month-level statistics are a retrospective evaluation and are kept separate from the decision replay. The product does not forecast wind and does not compute the utility's purchase volume.

## Use of AI tools

This project was built with substantial help from Claude Code (Anthropic's AI coding agent) for research, implementation, tests and documentation. Every design decision, the data checks and the final review were done by the author; the numbers above were reproduced from the committed snapshot with the scripts in this repository.
