import { useMemo } from "react";
import { useMetadata } from "./api/client";
import { ErrorBanner, Skeleton } from "./components/StatusBanner";
import AccuracyView from "./features/AccuracyView";
import ReplayView from "./features/ReplayView";
import { useUrlSelection, type Selection, type View } from "./state/urlState";

// A representative, verified January day used only when the URL carries no date.
const SAMPLE_DAY = "2026-01-10";

export default function App() {
  const meta = useMetadata();
  const defaults = useMemo<Selection>(() => {
    const min = meta.data?.decision_date_min ?? SAMPLE_DAY;
    const max = meta.data?.decision_date_max ?? SAMPLE_DAY;
    const sample = SAMPLE_DAY >= min && SAMPLE_DAY <= max ? SAMPLE_DAY : min;
    return { view: "replay", date: sample, from: min, to: max, cutoff: meta.data?.default_cutoff ?? "09:20", compare: "" };
  }, [meta.data]);
  const [sel, update] = useUrlSelection(defaults);
  const usingSample = !new URLSearchParams(window.location.search).has("date") && sel.view === "replay";

  return (
    <div className="app">
      <header className="app-header">
        <div>
          <h1>Wind forecast decision replay</h1>
          <div className="sub">
            GB day-ahead purchasing · January 2026 historical pilot · Elexon WINDFOR vs FUELHH (wind)
          </div>
        </div>
        <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
          {usingSample && <span className="pill sample">showing sample day</span>}
          {meta.data && (
            <span className="pill" title={`Built ${meta.data.built_at_utc}`}>
              snapshot {meta.data.snapshot_id}
            </span>
          )}
        </div>
      </header>

      <nav className="tabs" role="tablist" aria-label="Views">
        {(["replay", "accuracy"] as View[]).map((v) => (
          <button
            key={v}
            role="tab"
            type="button"
            aria-selected={sel.view === v}
            onClick={() => update({ view: v })}
          >
            {v === "replay" ? "1 · Decision replay" : "2 · Accuracy review"}
          </button>
        ))}
      </nav>

      {meta.isPending && <Skeleton label="Loading snapshot metadata" />}
      {meta.isError && <ErrorBanner error={meta.error} onRetry={() => meta.refetch()} />}
      {meta.data && sel.view === "replay" && <ReplayView meta={meta.data} sel={sel} update={update} />}
      {meta.data && sel.view === "accuracy" && <AccuracyView meta={meta.data} sel={sel} update={update} />}

      <footer>
        Contains BMRS data © Elexon Limited copyright and database right 2026. Times shown in UK local time
        (Europe/London). Historical replay only; not a forecast.
      </footer>
    </div>
  );
}
