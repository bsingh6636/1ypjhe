import { exportUrl, useAccuracy } from "../api/client";
import type { Comparison, Metadata } from "../api/types";
import CutoffPicker from "../components/CutoffPicker";
import Methodology from "../components/Methodology";
import MetricTiles from "../components/MetricTiles";
import { ErrorChart, OverlayChart } from "../components/charts";
import { ErrorBanner, Skeleton, WarnBanner } from "../components/StatusBanner";
import { DailyTable, IntervalTable } from "../components/tables";
import { clampDate, gwh, longDate, mw, signedMw, ukDayTime } from "../lib/format";
import type { Selection } from "../state/urlState";

interface Props {
  meta: Metadata;
  sel: Selection;
  update: (patch: Partial<Selection>) => void;
}

export default function AccuracyView({ meta, sel, update }: Props) {
  const min = meta.decision_date_min;
  const max = meta.decision_date_max;
  const otherPreset = meta.cutoff_presets.find((p) => p.time !== sel.cutoff)?.time ?? "";
  const compareOn = sel.compare !== "" && sel.compare !== sel.cutoff;
  const q = useAccuracy(sel.from, sel.to, sel.cutoff, compareOn ? sel.compare : undefined);
  const multiDay = sel.from !== sel.to;

  return (
    <>
      <div className="controls">
        <div className="field">
          <label htmlFor="from-date">Decision dates from</label>
          <input
            id="from-date"
            type="date"
            min={min}
            max={max}
            value={sel.from}
            onChange={(e) => {
              if (!e.target.value) return;
              const from = clampDate(e.target.value, min, max);
              update({ from, to: sel.to < from ? from : sel.to });
            }}
          />
        </div>
        <div className="field">
          <label htmlFor="to-date">to</label>
          <input
            id="to-date"
            type="date"
            min={min}
            max={max}
            value={sel.to}
            onChange={(e) => {
              if (!e.target.value) return;
              const to = clampDate(e.target.value, min, max);
              update({ to, from: sel.from > to ? to : sel.from });
            }}
          />
        </div>
        <button type="button" className="btn" onClick={() => update({ from: min, to: max })}>
          Whole of January
        </button>
        <CutoffPicker value={sel.cutoff} presets={meta.cutoff_presets} onChange={(cutoff) => update({ cutoff })} />
        <label className="checkbox">
          <input
            type="checkbox"
            checked={compareOn}
            disabled={!otherPreset}
            onChange={(e) => update({ compare: e.target.checked ? otherPreset : "" })}
          />
          Compare with {otherPreset || "other preset"}
        </label>
        <div className="spacer" />
        <a className="btn" href={exportUrl(sel.from, sel.to, sel.cutoff)} download>
          Download CSV
        </a>
      </div>

      {q.isPending && <Skeleton label="Loading accuracy review" />}
      {q.isError && <ErrorBanner error={q.error} onRetry={() => q.refetch()} />}
      {q.data && (
        <>
          <section aria-labelledby="acc-h">
            <h2 id="acc-h" style={{ marginBottom: 8 }}>
              {multiDay
                ? `Decisions ${longDate(q.data.decision_from)} to ${longDate(q.data.decision_to)} at ${q.data.cutoff} UK`
                : `Decision ${longDate(q.data.decision_from)} at ${q.data.cutoff} UK, delivery ${longDate(q.data.daily[0]?.delivery_date ?? q.data.decision_from)}`}
              {q.isFetching && <span className="pill" style={{ marginLeft: 8 }}>updating…</span>}
            </h2>
            <MetricTiles m={q.data.summary} />
            {q.data.summary.reason && <WarnBanner>No matched hours in this selection: {q.data.summary.reason}.</WarnBanner>}
            {q.data.summary.excluded > 0 && !q.data.summary.reason && (
              <WarnBanner>
                {q.data.summary.excluded} of {q.data.summary.expected} hours excluded. Metrics cover matched hours only.
              </WarnBanner>
            )}
          </section>

          <section className="card" aria-labelledby="ov-h">
            <h2 id="ov-h">Forecast against actual</h2>
            <div className="legend">
              <span>
                <span className="sw" style={{ background: "var(--forecast)" }} />
                Forecast (eligible at cutoff)
              </span>
              <span>
                <span className="sw" style={{ background: "var(--actual)" }} />
                Actual (hourly mean of half-hours)
              </span>
            </div>
            <OverlayChart rows={q.data.intervals} multiDay={multiDay} />
            <p className="hint">
              Forecast energy {gwh(q.data.summary.forecast_mwh)} vs actual {gwh(q.data.summary.actual_mwh)} over matched
              hours.
            </p>
          </section>

          <section className="card" aria-labelledby="err-h">
            <h2 id="err-h">Signed error per hour (forecast − actual)</h2>
            <div className="legend">
              <span>
                <span className="sw box" style={{ background: "var(--over)" }} />
                Over-forecast (buyer would be short)
              </span>
              <span>
                <span className="sw box" style={{ background: "var(--under)" }} />
                Under-forecast
              </span>
            </div>
            <ErrorChart rows={q.data.intervals} multiDay={multiDay} />
          </section>

          {q.data.comparison && <ComparisonPanel c={q.data.comparison} />}

          {multiDay ? (
            <section className="card" aria-labelledby="daily-h">
              <h2 id="daily-h">Daily summary</h2>
              <p className="hint">Select a day to drill into its 24 delivery hours.</p>
              <DailyTable days={q.data.daily} onSelect={(d) => update({ from: d, to: d })} />
            </section>
          ) : (
            <section className="card" aria-labelledby="int-h">
              <h2 id="int-h">Hour by hour</h2>
              <IntervalTable rows={q.data.intervals} />
              <p className="hint" style={{ marginTop: 8 }}>
                <button type="button" className="btn" onClick={() => update({ view: "replay", date: sel.from })}>
                  ← Back to the decision replay for this day
                </button>
              </p>
            </section>
          )}
          <Methodology snapshotId={q.data.snapshot_id} />
        </>
      )}
    </>
  );
}

function ComparisonPanel({ c }: { c: Comparison }) {
  const sides = [c.a, c.b];
  return (
    <section className="card" aria-labelledby="cmp-h">
      <h2 id="cmp-h">
        Cutoff comparison: {c.a.cutoff} vs {c.b.cutoff}
      </h2>
      <p className="hint">
        {c.note} {c.matched_hours} paired hours; the forecast differed in {c.hours_with_different_forecast} of them
        (mean absolute change {mw(c.mean_abs_forecast_change_mw)} MW).
      </p>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th scope="col">Cutoff</th>
              <th scope="col">Runs used</th>
              <th scope="col" className="num">Hours</th>
              <th scope="col" className="num">MAE</th>
              <th scope="col" className="num">RMSE</th>
              <th scope="col" className="num">Bias</th>
              <th scope="col" className="num">P90 abs</th>
            </tr>
          </thead>
          <tbody>
            {sides.map((s) => (
              <tr key={s.cutoff}>
                <td>{s.cutoff} UK</td>
                <td>{summariseRuns(s.runs_used)}</td>
                <td className="num">{s.metrics.n}</td>
                <td className="num">{mw(s.metrics.mae_mw)}</td>
                <td className="num">{mw(s.metrics.rmse_mw)}</td>
                <td className="num">{signedMw(s.metrics.bias_mw)}</td>
                <td className="num">{mw(s.metrics.p90_abs_mw)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function summariseRuns(runs: string[]): string {
  if (runs.length <= 3) return runs.map(ukDayTime).join(", ");
  const clocks = new Set(runs.map((r) => r.slice(11, 16)));
  return `${runs.length} runs (${[...clocks].sort().join(", ")} UTC)`;
}
