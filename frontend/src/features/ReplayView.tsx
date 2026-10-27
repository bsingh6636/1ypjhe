import { useReplay } from "../api/client";
import type { Metadata } from "../api/types";
import CutoffPicker from "../components/CutoffPicker";
import Methodology from "../components/Methodology";
import { ForecastChart } from "../components/charts";
import { ErrorBanner, Skeleton, WarnBanner } from "../components/StatusBanner";
import { ForecastTable } from "../components/tables";
import { addDays, age, clampDate, gwh, longDate, ukDayTime } from "../lib/format";
import type { Selection } from "../state/urlState";

interface Props {
  meta: Metadata;
  sel: Selection;
  update: (patch: Partial<Selection>) => void;
}

export default function ReplayView({ meta, sel, update }: Props) {
  const q = useReplay(sel.date, sel.cutoff);
  const min = meta.decision_date_min;
  const max = meta.decision_date_max;

  return (
    <>
      <div className="controls">
        <div className="field">
          <label htmlFor="decision-date">Decision date</label>
          <div style={{ display: "flex", gap: 6 }}>
            <button
              type="button"
              className="btn"
              aria-label="Previous day"
              disabled={sel.date <= min}
              onClick={() => update({ date: clampDate(addDays(sel.date, -1), min, max) })}
            >
              ‹
            </button>
            <input
              id="decision-date"
              type="date"
              min={min}
              max={max}
              value={sel.date}
              onChange={(e) => e.target.value && update({ date: clampDate(e.target.value, min, max) })}
            />
            <button
              type="button"
              className="btn"
              aria-label="Next day"
              disabled={sel.date >= max}
              onClick={() => update({ date: clampDate(addDays(sel.date, 1), min, max) })}
            >
              ›
            </button>
          </div>
        </div>
        <CutoffPicker value={sel.cutoff} presets={meta.cutoff_presets} onChange={(cutoff) => update({ cutoff })} />
        <div className="spacer" />
        <button
          type="button"
          className="btn primary"
          onClick={() => update({ view: "accuracy", from: sel.date, to: sel.date })}
        >
          Review performance →
        </button>
      </div>

      {q.isPending && <Skeleton label="Loading forecast" />}
      {q.isError && <ErrorBanner error={q.error} onRetry={() => q.refetch()} />}
      {q.data && (
        <>
          <section className="card" aria-labelledby="replay-h">
            <h2 id="replay-h">
              Buying for {longDate(q.data.delivery_date)} · decided {longDate(q.data.decision_date)} by {q.data.cutoff} UK
            </h2>
            <p className="hint">
              This is what the desk could see at the cutoff. Actual generation is deliberately hidden on this view.
            </p>
            <div className="facts">
              <div className="fact">
                <div className="k">Forecast run(s) used</div>
                <div className="v small">
                  {q.data.runs_used.length ? q.data.runs_used.map((r) => ukDayTime(r)).join(", ") : "none eligible"}
                </div>
              </div>
              <div className="fact">
                <div className="k">Newest run age at cutoff</div>
                <div className="v small">{age(Math.min(...q.data.points.filter((p) => p.age_minutes !== null).map((p) => p.age_minutes as number)) || null)}</div>
              </div>
              <div className="fact">
                <div className="k">Coverage</div>
                <div className="v">
                  {q.data.coverage.covered} / {q.data.coverage.expected} h
                </div>
              </div>
              <div className="fact">
                <div className="k">Forecast wind energy</div>
                <div className="v">{gwh(q.data.forecast_mwh)}</div>
              </div>
              <div className="fact">
                <div className="k">Cutoff (UTC)</div>
                <div className="v small mono">{q.data.cutoff_utc}</div>
              </div>
            </div>
            {q.data.coverage.missing > 0 && (
              <WarnBanner>
                {q.data.coverage.missing} of {q.data.coverage.expected} delivery hours had no forecast published by
                the cutoff. Gaps are shown as gaps, never filled.
              </WarnBanner>
            )}
          </section>

          <section className="card" aria-labelledby="chart-h">
            <h2 id="chart-h">Hourly wind forecast for the delivery day</h2>
            <div className="legend">
              <span>
                <span className="sw" style={{ background: "var(--forecast)" }} />
                Forecast, MW (step = hourly value)
              </span>
            </div>
            <ForecastChart points={q.data.points} />
          </section>

          <section className="card" aria-labelledby="table-h">
            <h2 id="table-h">Interval detail and provenance</h2>
            <ForecastTable points={q.data.points} />
            <Methodology snapshotId={q.data.snapshot_id} />
          </section>
        </>
      )}
    </>
  );
}
