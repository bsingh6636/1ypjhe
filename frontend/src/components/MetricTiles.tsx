import type { MetricsBlock } from "../api/types";
import { mw, signedMw } from "../lib/format";

export default function MetricTiles({ m }: { m: MetricsBlock }) {
  const biasNote =
    m.bias_mw === null ? "" : m.bias_mw > 0 ? "over-forecast on average" : m.bias_mw < 0 ? "under-forecast on average" : "no net bias";
  return (
    <div className="tiles" aria-label="Accuracy metrics">
      <Tile k="MAE" v={mw(m.mae_mw)} u="MW" d="typical absolute miss per hour" />
      <Tile k="RMSE" v={mw(m.rmse_mw)} u="MW" d="penalises large misses" />
      <Tile k="Bias" v={signedMw(m.bias_mw)} u="MW" d={biasNote} />
      <Tile k="P90 abs error" v={mw(m.p90_abs_mw)} u="MW" d="9 in 10 hours missed by less" />
      <Tile
        k="Coverage"
        v={`${m.n} / ${m.expected}`}
        u="hours"
        d={m.excluded ? `${m.excluded} excluded (no forecast or incomplete actual)` : "all hours matched"}
      />
    </div>
  );
}

function Tile({ k, v, u, d }: { k: string; v: string; u?: string; d?: string }) {
  return (
    <div className="tile">
      <div className="k">{k}</div>
      <div className="v">
        {v}
        {u && <span className="u">{u}</span>}
      </div>
      {d && <div className="d">{d}</div>}
    </div>
  );
}
