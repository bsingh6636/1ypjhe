// All user selections live in the URL so a link reproduces the exact view. Nothing is copied into global state.
import { useCallback, useSyncExternalStore } from "react";

export type View = "replay" | "accuracy";

export interface Selection {
  view: View;
  date: string; // decision date for the replay view (YYYY-MM-DD)
  from: string; // accuracy range start (decision date)
  to: string; // accuracy range end (decision date)
  cutoff: string; // HH:MM UK local time
  compare: string; // second cutoff for the paired comparison, "" when off
}

export const CUTOFF_RE = /^(?:[01]\d|2[0-3]):[0-5]\d$/;
const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

export function parseSelection(search: string, defaults: Selection): Selection {
  const p = new URLSearchParams(search);
  const date = p.get("date");
  const from = p.get("from");
  const to = p.get("to");
  const cutoff = p.get("cutoff");
  const compare = p.get("compare");
  return {
    view: p.get("view") === "accuracy" ? "accuracy" : "replay",
    date: date && DATE_RE.test(date) ? date : defaults.date,
    from: from && DATE_RE.test(from) ? from : defaults.from,
    to: to && DATE_RE.test(to) ? to : defaults.to,
    cutoff: cutoff && CUTOFF_RE.test(cutoff) ? cutoff : defaults.cutoff,
    compare: compare && CUTOFF_RE.test(compare) ? compare : "",
  };
}

export function serialiseSelection(s: Selection): string {
  const p = new URLSearchParams();
  p.set("view", s.view);
  if (s.view === "replay") p.set("date", s.date);
  else {
    p.set("from", s.from);
    p.set("to", s.to);
  }
  p.set("cutoff", s.cutoff);
  if (s.compare) p.set("compare", s.compare);
  return `?${p.toString()}`;
}

const listeners = new Set<() => void>();
function subscribe(cb: () => void) {
  listeners.add(cb);
  window.addEventListener("popstate", cb);
  return () => {
    listeners.delete(cb);
    window.removeEventListener("popstate", cb);
  };
}
function getSnapshot() {
  return window.location.search;
}

export function useUrlSelection(defaults: Selection): [Selection, (patch: Partial<Selection>) => void] {
  const search = useSyncExternalStore(subscribe, getSnapshot, getSnapshot);
  const selection = parseSelection(search, defaults);
  const update = useCallback(
    (patch: Partial<Selection>) => {
      const next = { ...parseSelection(window.location.search, defaults), ...patch };
      const qs = serialiseSelection(next);
      if (qs !== window.location.search) {
        window.history.pushState(null, "", qs);
        listeners.forEach((l) => l());
      }
    },
    [defaults],
  );
  return [selection, update];
}
