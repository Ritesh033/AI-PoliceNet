import type { CategoryId, Incident, Period, PeriodSeries, Stage, Triage } from '../types';
import { CATEGORIES, COMPLAINT_BASE, PERIODS, PRIORITY_RANK, REGIONS, TRIAGE } from '../data/constants';
import { allocate } from '../lib/random';
import type { LiveExtras } from './consoleState';

export interface PeriodStats {
  total: number;
  previousTotal: number;
  perCategory: Record<CategoryId, number>;
  triage: Record<Triage, number>;
}

/** Live (simulated) alerts are added to the newest bucket, so they count toward every period. */
export function periodStats(series: PeriodSeries, extras: LiveExtras): PeriodStats {
  const perCategory = { threat: 0, scam: 0, ncii: 0, hate: 0, manipulated: 0 } as Record<CategoryId, number>;
  for (const b of series.buckets) for (const c of CATEGORIES) perCategory[c.id] += b.counts[c.id];
  const base = CATEGORIES.reduce((n, c) => n + perCategory[c.id], 0);
  const parts = allocate(base, TRIAGE.map((t) => t.weight));
  const triage = { urgent: parts[0], review: parts[1], none: parts[2] } as Record<Triage, number>;
  for (const c of CATEGORIES) perCategory[c.id] += extras.byCategory[c.id];
  for (const t of TRIAGE) triage[t.id] += extras.byTriage[t.id];
  return {
    total: base + extras.total,
    previousTotal: series.previousTotal,
    perCategory,
    triage,
  };
}

export function withExtras(series: PeriodSeries, extras: LiveExtras) {
  const buckets = series.buckets.map((b, i) => {
    if (i !== series.buckets.length - 1) return b;
    const counts = { ...b.counts };
    for (const c of CATEGORIES) counts[c.id] += extras.byCategory[c.id];
    return { ...b, counts, total: b.total + extras.total };
  });
  return buckets;
}

export function countByStage(incidents: readonly Incident[]): Record<Stage, number> {
  const out: Record<Stage, number> = { awaiting: 0, in_review: 0, referred: 0, closed: 0 };
  for (const i of incidents) out[i.stage] += 1;
  return out;
}

export function urgentReferrals(incidents: readonly Incident[], period: Period, now: number) {
  const ms = PERIODS.find((p) => p.id === period)!.ms;
  let current = 0;
  let previous = 0;
  for (const i of incidents) {
    if (i.priority !== 'urgent' || i.stage !== 'referred' || i.referredAt === undefined) continue;
    const age = now - i.referredAt;
    if (age < ms) current += 1;
    else if (age < 2 * ms) previous += 1;
  }
  return { current, previous };
}

export function awaitingCount(incidents: readonly Incident[]) {
  const waiting = incidents.filter((i) => i.stage === 'awaiting');
  const oldest = waiting.reduce<number | null>(
    (min, i) => (min === null || i.receivedAt < min ? i.receivedAt : min),
    null,
  );
  return { count: waiting.length, social: waiting.filter((i) => i.kind === 'social').length, oldest };
}

export function openComplaints(incidents: readonly Incident[]) {
  const conduct = incidents.filter((i) => i.kind === 'conduct');
  const supervisor = conduct.filter((i) => i.stage === 'awaiting' || i.stage === 'in_review').length;
  const routed = conduct.filter((i) => i.stage === 'referred').length;
  const stages = [
    { id: 'acknowledged', label: 'Acknowledged', note: 'Awaiting assignment', value: COMPLAINT_BASE.acknowledged },
    { id: 'supervisor', label: 'Supervisor review', note: 'In the review queue', value: supervisor },
    { id: 'investigation', label: 'Investigation', note: 'Under inquiry', value: COMPLAINT_BASE.investigation + routed },
    { id: 'finding', label: 'Finding issued', note: 'Open to response', value: COMPLAINT_BASE.finding },
    { id: 'appeal', label: 'Appeal window', note: 'Appeal rights open', value: COMPLAINT_BASE.appeal },
  ];
  return { total: stages.reduce((n, s) => n + s.value, 0), stages };
}

export function awaitingByState(incidents: readonly Incident[]) {
  const counts = new Map<string, number>(REGIONS.map((r) => [r.state, 0]));
  for (const i of incidents) if (i.stage === 'awaiting') counts.set(i.state, (counts.get(i.state) ?? 0) + 1);
  return [...counts.entries()]
    .map(([state, value]) => ({ state, value }))
    .sort((a, b) => b.value - a.value || a.state.localeCompare(b.state));
}

/** Sort for the review queue: soonest deadline first for active work. */
export function sortQueue(incidents: readonly Incident[], stage: Stage): Incident[] {
  const list = incidents.filter((i) => i.stage === stage);
  switch (stage) {
    case 'awaiting':
    case 'in_review':
      return list.sort(
        (a, b) => a.dueAt - b.dueAt || PRIORITY_RANK[a.priority] - PRIORITY_RANK[b.priority] || a.id.localeCompare(b.id),
      );
    case 'referred':
      return list.sort((a, b) => (b.referredAt ?? 0) - (a.referredAt ?? 0));
    case 'closed':
      return list.sort((a, b) => b.receivedAt - a.receivedAt);
  }
}
