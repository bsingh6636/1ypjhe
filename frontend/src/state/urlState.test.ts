import { describe, expect, it } from "vitest";
import { parseSelection, serialiseSelection, type Selection } from "./urlState";

const defaults: Selection = { view: "replay", date: "2026-01-10", from: "2026-01-01", to: "2026-01-31", cutoff: "09:20", compare: "" };

describe("URL selection state", () => {
  it("falls back to defaults for missing or malformed params", () => {
    expect(parseSelection("", defaults)).toEqual(defaults);
    expect(parseSelection("?date=nope&cutoff=9:20&view=weird", defaults)).toEqual(defaults);
  });
  it("round-trips a full selection", () => {
    const s: Selection = { ...defaults, view: "accuracy", from: "2026-01-05", to: "2026-01-09", cutoff: "09:50", compare: "09:20" };
    expect(parseSelection(serialiseSelection(s), defaults)).toEqual(s);
  });
  it("omits irrelevant keys per view", () => {
    expect(serialiseSelection(defaults)).toBe("?view=replay&date=2026-01-10&cutoff=09%3A20");
  });
});
