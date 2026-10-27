import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import type { AccuracyResponse, Metadata, ReplayResponse } from "./api/types";

const metadata: Metadata = {
  snapshot_id: "abc123",
  built_at_utc: "2026-10-27T00:00:00+00:00",
  decision_date_min: "2026-01-01",
  decision_date_max: "2026-01-31",
  timezone: "Europe/London",
  units: "MW",
  methodology_version: "1.0",
  forecast_rows: 1,
  forecast_runs: 1,
  actual_rows: 1,
  cutoff_presets: [
    { key: "epex", label: "EPEX", time: "09:20" },
    { key: "n2ex", label: "N2EX", time: "09:50" },
  ],
  default_cutoff: "09:20",
  source: {},
};

function replayFor(cutoff: string): ReplayResponse {
  const run = cutoff === "09:50" ? "2026-01-10T09:30:00Z" : "2026-01-10T07:30:00Z";
  return {
    decision_date: "2026-01-10",
    delivery_date: "2026-01-11",
    cutoff,
    cutoff_utc: `2026-01-10T${cutoff}:00Z`,
    timezone: "Europe/London",
    snapshot_id: "abc123",
    runs_used: [run],
    coverage: { expected: 24, covered: 23, missing: 1 },
    points: Array.from({ length: 24 }, (_, i) => ({
      start_time: `2026-01-11T${String(i).padStart(2, "0")}:00:00Z`,
      forecast_mw: i === 22 ? null : 5000 + i * 10,
      publish_time: i === 22 ? null : run,
      age_minutes: i === 22 ? null : 110,
      lead_hours: i === 22 ? null : 16.5 + i,
    })),
    forecast_mwh: 120000,
  };
}

const accuracy: AccuracyResponse = {
  decision_from: "2026-01-10",
  decision_to: "2026-01-10",
  cutoff: "09:20",
  timezone: "Europe/London",
  snapshot_id: "abc123",
  summary: { n: 22, expected: 24, excluded: 2, mae_mw: 2039, rmse_mw: 2505, bias_mw: 1748, p90_abs_mw: 4096, forecast_mwh: 1, actual_mwh: 1, reason: null },
  daily: [{ decision_date: "2026-01-10", delivery_date: "2026-01-11", cutoff_utc: "2026-01-10T09:20:00Z", runs_used: ["2026-01-10T07:30:00Z"], metrics: { n: 22, expected: 24, excluded: 2, mae_mw: 2039, rmse_mw: 2505, bias_mw: 1748, p90_abs_mw: 4096, forecast_mwh: 1, actual_mwh: 1, reason: null } }],
  intervals: [{ decision_date: "2026-01-10", start_time: "2026-01-11T00:00:00Z", forecast_mw: 5000, actual_mw: 4000, error_mw: 1000, publish_time: "2026-01-10T07:30:00Z", excluded_reason: null }],
  comparison: null,
};

function mockFetch() {
  return vi.fn(async (input: RequestInfo | URL) => {
    const url = new URL(String(input), "http://localhost");
    const json = (body: unknown) => new Response(JSON.stringify(body), { status: 200, headers: { "content-type": "application/json" } });
    if (url.pathname.endsWith("/metadata")) return json(metadata);
    if (url.pathname.endsWith("/forecast")) return json(replayFor(url.searchParams.get("cutoff") ?? "09:20"));
    if (url.pathname.endsWith("/accuracy")) return json(accuracy);
    return new Response(JSON.stringify({ detail: "not found" }), { status: 404 });
  });
}

function renderApp(search: string) {
  window.history.replaceState(null, "", search || "/");
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <App />
    </QueryClientProvider>,
  );
}

describe("App", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", mockFetch());
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("replays the selected day and shows provenance, coverage and gaps", async () => {
    renderApp("?view=replay&date=2026-01-10&cutoff=09:20");
    expect(await screen.findByText(/Buying for Sun 11 Jan 2026/)).toBeInTheDocument();
    expect(screen.getAllByText("10 Jan 07:30").length).toBeGreaterThan(0); // run used (summary + table)
    expect(screen.getByText(/23 \/ 24 h/)).toBeInTheDocument();
    expect(screen.getByText(/1 of 24 delivery hours had no forecast/)).toBeInTheDocument();
    expect(screen.getByText("snapshot abc123")).toBeInTheDocument();
  });

  it("changing the cutoff preset updates the URL and selects a different run", async () => {
    renderApp("?view=replay&date=2026-01-10&cutoff=09:20");
    await screen.findByText(/Buying for/);
    await userEvent.click(screen.getByRole("button", { name: /N2EX 09:50/ }));
    await waitFor(() => expect(window.location.search).toContain("cutoff=09%3A50"));
    expect((await screen.findAllByText("10 Jan 09:30")).length).toBeGreaterThan(0);
    expect(screen.queryByText("10 Jan 07:30")).not.toBeInTheDocument();
  });

  it("navigates to the accuracy review for the same day and renders metrics", async () => {
    renderApp("?view=replay&date=2026-01-10&cutoff=09:20");
    await screen.findByText(/Buying for/);
    await userEvent.click(screen.getByRole("button", { name: /Review performance/ }));
    expect(window.location.search).toContain("view=accuracy");
    expect(window.location.search).toContain("from=2026-01-10");
    expect(await screen.findByText("2,039")).toBeInTheDocument(); // MAE tile
    expect(screen.getByText("+1,748")).toBeInTheDocument(); // bias tile
    expect(screen.getByRole("link", { name: /Download CSV/ })).toHaveAttribute(
      "href",
      expect.stringContaining("/api/v1/export.csv?decision_from=2026-01-10"),
    );
  });

  it("shows an error banner with retry when the API fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(JSON.stringify({ detail: "snapshot not found" }), { status: 503 })),
    );
    renderApp("?view=replay&date=2026-01-10");
    expect(await screen.findByRole("alert")).toHaveTextContent(/503: snapshot not found/);
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });
});
