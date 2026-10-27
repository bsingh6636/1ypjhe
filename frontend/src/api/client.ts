import { useQuery } from "@tanstack/react-query";
import type { AccuracyResponse, Metadata, ReplayResponse } from "./types";

const BASE = "/api/v1";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function getJson<T>(path: string, params: Record<string, string | undefined>, signal?: AbortSignal): Promise<T> {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== "") qs.set(k, v);
  const url = qs.size ? `${BASE}${path}?${qs}` : `${BASE}${path}`;
  const res = await fetch(url, { signal, headers: { accept: "application/json" } });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, detail);
  }
  return (await res.json()) as T;
}

export function exportUrl(from: string, to: string, cutoff: string): string {
  const qs = new URLSearchParams({ decision_from: from, decision_to: to, cutoff });
  return `${BASE}/export.csv?${qs}`;
}

export function useMetadata() {
  return useQuery({
    queryKey: ["metadata"],
    queryFn: ({ signal }) => getJson<Metadata>("/metadata", {}, signal),
    staleTime: Infinity,
  });
}

export function useReplay(decisionDate: string | undefined, cutoff: string) {
  return useQuery({
    queryKey: ["forecast", decisionDate, cutoff],
    queryFn: ({ signal }) => getJson<ReplayResponse>("/forecast", { decision_date: decisionDate, cutoff }, signal),
    enabled: Boolean(decisionDate),
  });
}

export function useAccuracy(from: string | undefined, to: string | undefined, cutoff: string, compare?: string) {
  return useQuery({
    queryKey: ["accuracy", from, to, cutoff, compare ?? ""],
    queryFn: ({ signal }) =>
      getJson<AccuracyResponse>(
        "/accuracy",
        { decision_from: from, decision_to: to, cutoff, compare_cutoff: compare },
        signal,
      ),
    enabled: Boolean(from && to),
    placeholderData: (prev) => prev,
  });
}
