import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ForecastPoint, IntervalRow } from "../api/types";
import { mw, signedMw, ukDayTime, ukTime } from "../lib/format";

const css = (name: string) =>
  typeof window === "undefined" ? "" : getComputedStyle(document.documentElement).getPropertyValue(name).trim();

function axisStyle() {
  return { stroke: css("--axis") || "#c3c2b7", tick: { fill: css("--muted") || "#898781", fontSize: 12 } };
}

const mwTick = (v: number) => (v >= 1000 ? `${Math.round(v / 100) / 10}k` : String(v));

export function ForecastChart({ points, multiDay }: { points: ForecastPoint[]; multiDay?: boolean }) {
  const data = points.map((p) => ({ ...p, t: p.start_time }));
  const ax = axisStyle();
  return (
    <div className="chart" role="img" aria-label="Hourly wind forecast for the delivery day, MW">
      <ResponsiveContainer>
        <LineChart data={data} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
          <CartesianGrid stroke={css("--grid") || "#e1e0d9"} vertical={false} />
          <XAxis dataKey="t" tickFormatter={multiDay ? ukDayTime : ukTime} {...ax} minTickGap={24} />
          <YAxis tickFormatter={mwTick} width={44} {...ax} />
          <Tooltip content={<ForecastTooltip />} />
          <Line
            type="stepAfter"
            dataKey="forecast_mw"
            name="Forecast"
            stroke={css("--forecast") || "#2a78d6"}
            strokeWidth={2}
            dot={false}
            connectNulls={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function ForecastTooltip({ active, payload }: { active?: boolean; payload?: Array<{ payload: ForecastPoint }> }) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  return (
    <div className="tooltip">
      <div className="t">{ukDayTime(p.start_time)} UK</div>
      <div className="row">
        <span>Forecast</span>
        <span>{mw(p.forecast_mw)} MW</span>
      </div>
      <div className="row dim">
        <span>Published</span>
        <span>{p.publish_time ? ukDayTime(p.publish_time) : "no eligible run"}</span>
      </div>
      {p.lead_hours !== null && (
        <div className="row dim">
          <span>Lead time</span>
          <span>{p.lead_hours} h</span>
        </div>
      )}
    </div>
  );
}

export function OverlayChart({ rows, multiDay }: { rows: IntervalRow[]; multiDay?: boolean }) {
  const ax = axisStyle();
  return (
    <div className="chart tall" role="img" aria-label="Forecast and actual wind generation, MW">
      <ResponsiveContainer>
        <LineChart data={rows} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
          <CartesianGrid stroke={css("--grid") || "#e1e0d9"} vertical={false} />
          <XAxis dataKey="start_time" tickFormatter={multiDay ? ukDayTime : ukTime} {...ax} minTickGap={24} />
          <YAxis tickFormatter={mwTick} width={44} {...ax} />
          <Tooltip content={<OverlayTooltip />} />
          <Line
            type="stepAfter"
            dataKey="forecast_mw"
            name="Forecast"
            stroke={css("--forecast") || "#2a78d6"}
            strokeWidth={2}
            dot={false}
            connectNulls={false}
            isAnimationActive={false}
          />
          <Line
            type="stepAfter"
            dataKey="actual_mw"
            name="Actual"
            stroke={css("--actual") || "#eb6834"}
            strokeWidth={2}
            dot={false}
            connectNulls={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function OverlayTooltip({ active, payload }: { active?: boolean; payload?: Array<{ payload: IntervalRow }> }) {
  if (!active || !payload?.length) return null;
  const r = payload[0].payload;
  return (
    <div className="tooltip">
      <div className="t">{ukDayTime(r.start_time)} UK</div>
      <div className="row">
        <span>Forecast</span>
        <span>{mw(r.forecast_mw)} MW</span>
      </div>
      <div className="row">
        <span>Actual (hourly mean)</span>
        <span>{mw(r.actual_mw)} MW</span>
      </div>
      <div className="row">
        <span>Error</span>
        <span>{signedMw(r.error_mw)} MW</span>
      </div>
      {r.excluded_reason && <div className="row dim">{r.excluded_reason}</div>}
    </div>
  );
}

export function ErrorChart({ rows, multiDay }: { rows: IntervalRow[]; multiDay?: boolean }) {
  const ax = axisStyle();
  const over = css("--over") || "#eb6834";
  const under = css("--under") || "#2a78d6";
  return (
    <div className="chart" role="img" aria-label="Signed forecast error per hour, forecast minus actual, MW">
      <ResponsiveContainer>
        <BarChart data={rows} margin={{ top: 8, right: 12, left: 0, bottom: 0 }} barCategoryGap={multiDay ? 0 : 2}>
          <CartesianGrid stroke={css("--grid") || "#e1e0d9"} vertical={false} />
          <XAxis dataKey="start_time" tickFormatter={multiDay ? ukDayTime : ukTime} {...ax} minTickGap={24} />
          <YAxis tickFormatter={mwTick} width={44} {...ax} />
          <ReferenceLine y={0} stroke={css("--axis") || "#c3c2b7"} />
          <Tooltip content={<OverlayTooltip />} cursor={{ fill: "rgba(128,128,128,0.12)" }} />
          <Bar dataKey="error_mw" name="Error" isAnimationActive={false} radius={[3, 3, 0, 0]}>
            {rows.map((r) => (
              <Cell key={r.start_time} fill={(r.error_mw ?? 0) >= 0 ? over : under} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
