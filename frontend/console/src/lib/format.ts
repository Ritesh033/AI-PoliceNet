const TZ = 'Asia/Kolkata';
const MIN = 60_000;
const HOUR = 60 * MIN;
const DAY = 24 * HOUR;

export const TIME = { MIN, HOUR, DAY } as const;

const intFmt = new Intl.NumberFormat('en-IN');

export function fmtInt(n: number): string {
  return intFmt.format(Math.round(n));
}

export function fmtCompact(n: number): string {
  if (Math.abs(n) < 1000) return String(Math.round(n));
  const k = n / 1000;
  return `${Number.isInteger(k) ? k : k.toFixed(1)}K`;
}

export function fmtPct(fraction: number, digits = 0): string {
  return `${(fraction * 100).toFixed(digits)}%`;
}

const dateTimeFmt = new Intl.DateTimeFormat('en-IN', {
  day: 'numeric',
  month: 'short',
  hour: 'numeric',
  minute: '2-digit',
  hour12: true,
  timeZone: TZ,
});

export function fmtDateTime(ts: number): string {
  return `${dateTimeFmt.format(ts)} IST`;
}

const clockFmt = new Intl.DateTimeFormat('en-GB', {
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
  hour12: false,
  timeZone: TZ,
});

export function fmtClock(ts: number): string {
  return clockFmt.format(ts);
}

const dayLabelFmt = new Intl.DateTimeFormat('en-IN', { day: 'numeric', month: 'short', timeZone: TZ });
const weekdayFmt = new Intl.DateTimeFormat('en-IN', { weekday: 'short', day: 'numeric', timeZone: TZ });

export function fmtDayLabel(ts: number): string {
  return dayLabelFmt.format(ts);
}

export function fmtWeekdayLabel(ts: number): string {
  return weekdayFmt.format(ts);
}

/** Hour of day (0-23) in IST. */
export function istHour(ts: number): number {
  return new Date(ts + 5.5 * HOUR).getUTCHours();
}

export function fmtHourLabel(ts: number): string {
  return `${String(istHour(ts)).padStart(2, '0')}:00`;
}

function duration(ms: number): string {
  const mins = Math.max(1, Math.round(ms / MIN));
  if (mins < 60) return `${mins} min`;
  const hours = Math.floor(mins / 60);
  const rest = mins % 60;
  if (hours < 48) return rest === 0 ? `${hours} h` : `${hours} h ${String(rest).padStart(2, '0')} min`;
  return `${Math.floor(hours / 24)} d`;
}

export function ago(ts: number, now: number): string {
  const diff = now - ts;
  if (diff < MIN) return 'just now';
  return `${duration(diff)} ago`;
}

export function waited(ts: number, now: number): string {
  return duration(now - ts);
}

export function dueLabel(dueAt: number, now: number): { text: string; overdue: boolean } {
  const diff = dueAt - now;
  if (diff < 0) return { text: `Overdue by ${duration(-diff)}`, overdue: true };
  return { text: `Due in ${duration(diff)}`, overdue: false };
}
