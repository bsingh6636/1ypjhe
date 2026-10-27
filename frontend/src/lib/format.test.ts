import { describe, expect, it } from "vitest";
import { addDays, age, clampDate, gwh, longDate, mw, signedMw, ukDayTime, ukTime } from "./format";

describe("format (pinned to Europe/London regardless of browser timezone)", () => {
  it("renders January UTC instants as GMT wall-clock", () => {
    expect(ukTime("2026-01-11T00:00:00Z")).toBe("00:00");
    expect(ukDayTime("2026-01-10T07:30:00Z")).toBe("10 Jan 07:30");
  });
  it("shifts summer instants to BST", () => {
    expect(ukTime("2026-07-10T08:20:00Z")).toBe("09:20");
  });
  it("formats calendar dates without timezone drift", () => {
    expect(longDate("2026-01-31")).toBe("Sat 31 Jan 2026");
    expect(addDays("2026-01-31", 1)).toBe("2026-02-01");
    expect(clampDate("2025-12-31", "2026-01-01", "2026-01-31")).toBe("2026-01-01");
  });
  it("formats numbers and nulls", () => {
    expect(mw(12345.6)).toBe("12,346");
    expect(mw(null)).toBe("–");
    expect(signedMw(1748.2)).toBe("+1,748");
    expect(signedMw(-50)).toBe("-50");
    expect(gwh(123456)).toBe("123.5 GWh");
    expect(age(110)).toBe("1 h 50 min");
    expect(age(5)).toBe("5 min");
  });
});
