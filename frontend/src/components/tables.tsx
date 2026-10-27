import type { DailySummary, ForecastPoint, IntervalRow } from "../api/types";
import { age, longDate, mw, shortDate, signedMw, ukDayTime, ukTime } from "../lib/format";

export function ForecastTable({ points }: { points: ForecastPoint[] }) {
  return (
    <div className="table-wrap">
      <table>
        <caption className="sr-only">Hourly forecast with publication provenance</caption>
        <thead>
          <tr>
            <th scope="col">Delivery hour (UK)</th>
            <th scope="col" className="num">
              Forecast MW
            </th>
            <th scope="col">Published (UK)</th>
            <th scope="col">Age at cutoff</th>
            <th scope="col" className="num">
              Lead time
            </th>
          </tr>
        </thead>
        <tbody>
          {points.map((p) => (
            <tr key={p.start_time} className={p.forecast_mw === null ? "excluded" : undefined}>
              <td>{ukTime(p.start_time)}</td>
              <td className="num">{p.forecast_mw === null ? <span className="gap">no eligible run</span> : mw(p.forecast_mw)}</td>
              <td>{p.publish_time ? ukDayTime(p.publish_time) : "–"}</td>
              <td>{age(p.age_minutes)}</td>
              <td className="num">{p.lead_hours === null ? "–" : `${p.lead_hours} h`}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function IntervalTable({ rows }: { rows: IntervalRow[]; }) {
  return (
    <div className="table-wrap" style={{ maxHeight: 420, overflowY: "auto" }}>
      <table>
        <caption className="sr-only">Evaluated hours: forecast, actual and signed error</caption>
        <thead>
          <tr>
            <th scope="col">Delivery hour (UK)</th>
            <th scope="col" className="num">
              Forecast MW
            </th>
            <th scope="col" className="num">
              Actual MW
            </th>
            <th scope="col" className="num">
              Error MW
            </th>
            <th scope="col">Forecast published</th>
            <th scope="col">Note</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.start_time} className={r.excluded_reason ? "excluded" : undefined}>
              <td>{ukDayTime(r.start_time)}</td>
              <td className="num">{mw(r.forecast_mw)}</td>
              <td className="num">{mw(r.actual_mw)}</td>
              <td className="num">{signedMw(r.error_mw)}</td>
              <td>{r.publish_time ? ukDayTime(r.publish_time) : "–"}</td>
              <td>{r.excluded_reason ?? ""}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function DailyTable({ days, onSelect }: { days: DailySummary[]; onSelect: (decisionDate: string) => void }) {
  return (
    <div className="table-wrap">
      <table>
        <caption className="sr-only">Daily accuracy summary; select a row to drill into that day</caption>
        <thead>
          <tr>
            <th scope="col">Decision</th>
            <th scope="col">Delivery</th>
            <th scope="col">Run(s) used</th>
            <th scope="col" className="num">
              Hours
            </th>
            <th scope="col" className="num">
              MAE
            </th>
            <th scope="col" className="num">
              RMSE
            </th>
            <th scope="col" className="num">
              Bias
            </th>
            <th scope="col" className="num">
              P90 abs
            </th>
            <th scope="col"></th>
          </tr>
        </thead>
        <tbody>
          {days.map((d) => (
            <tr
              key={d.decision_date}
              className="clickable"
              onClick={() => onSelect(d.decision_date)}
              title={`Open ${longDate(d.decision_date)}`}
            >
              <td>{shortDate(d.decision_date)}</td>
              <td>{shortDate(d.delivery_date)}</td>
              <td>{d.runs_used.map((r) => ukDayTime(r)).join(", ") || "none"}</td>
              <td className="num">
                {d.metrics.n}/{d.metrics.expected}
              </td>
              <td className="num">{mw(d.metrics.mae_mw)}</td>
              <td className="num">{mw(d.metrics.rmse_mw)}</td>
              <td className="num">{signedMw(d.metrics.bias_mw)}</td>
              <td className="num">{mw(d.metrics.p90_abs_mw)}</td>
              <td>
                <button
                  type="button"
                  className="btn"
                  style={{ minHeight: 28, padding: "2px 8px" }}
                  onClick={(e) => {
                    e.stopPropagation();
                    onSelect(d.decision_date);
                  }}
                  aria-label={`Drill into decision ${d.decision_date}`}
                >
                  Open
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
