// Formatting is pinned to Europe/London so the browser's own timezone can never shift a date or hour.
const TZ = "Europe/London";

const timeFmt = new Intl.DateTimeFormat("en-GB", { timeZone: TZ, hour: "2-digit", minute: "2-digit", hour12: false });
const dayTimeFmt = new Intl.DateTimeFormat("en-GB", {
  timeZone: TZ,
  day: "2-digit",
  month: "short",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});
const longDateFmt = new Intl.DateTimeFormat("en-GB", {
  timeZone: TZ,
  weekday: "short",
  day: "numeric",
  month: "short",
  year: "numeric",
});
const shortDateFmt = new Intl.DateTimeFormat("en-GB", { timeZone: TZ, day: "2-digit", month: "short" });
const mwFmt = new Intl.NumberFormat("en-GB", { maximumFractionDigits: 0 });
const gwhFmt = new Intl.NumberFormat("en-GB", { maximumFractionDigits: 1 });

export function ukTime(iso: string): string {
  return timeFmt.format(new Date(iso));
}

export function ukDayTime(iso: string): string {
  return dayTimeFmt.format(new Date(iso)).replace(",", "");
}

/** YYYY-MM-DD (a calendar date, not an instant) -> "Sun 11 Jan 2026". */
export function longDate(ymd: string): string {
  return longDateFmt.format(new Date(`${ymd}T12:00:00Z`)).replace(",", "");
}

export function shortDate(ymd: string): string {
  return shortDateFmt.format(new Date(`${ymd}T12:00:00Z`));
}

export function mw(value: number | null | undefined): string {
  return value === null || value === undefined ? "–" : mwFmt.format(value);
}

export function signedMw(value: number | null | undefined): string {
  if (value === null || value === undefined) return "–";
  return (value > 0 ? "+" : "") + mwFmt.format(value);
}

export function gwh(valueMwh: number | null | undefined): string {
  return valueMwh === null || valueMwh === undefined ? "–" : `${gwhFmt.format(valueMwh / 1000)} GWh`;
}

export function age(minutes: number | null | undefined): string {
  if (minutes === null || minutes === undefined) return "–";
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return h ? `${h} h ${m.toString().padStart(2, "0")} min` : `${m} min`;
}

export function addDays(ymd: string, days: number): string {
  const d = new Date(`${ymd}T12:00:00Z`);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

export function clampDate(ymd: string, min: string, max: string): string {
  if (ymd < min) return min;
  if (ymd > max) return max;
  return ymd;
}
