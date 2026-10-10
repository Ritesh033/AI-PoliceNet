import { describe, expect, it } from 'vitest';
import { buildSeed, TARGETS } from './seed';
import { awaitingCount, countByStage, openComplaints, periodStats, urgentReferrals } from '../state/selectors';
import { emptyExtras } from '../state/consoleState';
import { allocate, mulberry32 } from '../lib/random';

const ANCHOR = Date.UTC(2026, 9, 10, 10, 30);

describe('allocate', () => {
  it('always sums to the requested total', () => {
    const parts = allocate(1284, [0.34, 0.26, 0.17, 0.14, 0.09]);
    expect(parts.reduce((a, b) => a + b, 0)).toBe(1284);
  });
});

describe('mock seed data', () => {
  const seed = buildSeed(ANCHOR);
  const extras = emptyExtras();

  it('is deterministic for a given anchor', () => {
    expect(buildSeed(ANCHOR).incidents.map((i) => i.id + i.priority)).toEqual(
      seed.incidents.map((i) => i.id + i.priority),
    );
  });

  it('matches the prototype headline figures', () => {
    expect(periodStats(seed.series['7d'], extras).total).toBe(TARGETS.alerts7d);
    expect(awaitingCount(seed.incidents).count).toBe(TARGETS.awaitingReview);
    expect(awaitingCount(seed.incidents).social).toBe(TARGETS.awaitingSocial);
    expect(urgentReferrals(seed.incidents, '7d', ANCHOR).current).toBe(TARGETS.urgentReferrals7d);
    expect(openComplaints(seed.incidents).total).toBe(TARGETS.openComplaints);
  });

  it('keeps hourly and daily totals consistent', () => {
    const hourly = periodStats(seed.series['24h'], extras).total;
    const lastDay = seed.series['7d'].buckets.at(-1)!.total;
    expect(hourly).toBe(lastDay);
    expect(seed.series['24h'].buckets).toHaveLength(24);
    expect(seed.series['30d'].buckets).toHaveLength(30);
  });

  it('splits triage outcomes exactly', () => {
    const { triage, total } = periodStats(seed.series['7d'], extras);
    expect(triage.urgent + triage.review + triage.none).toBe(total);
  });

  it('uses unique ids and puts the three prototype items first', () => {
    const ids = seed.incidents.map((i) => i.id);
    expect(new Set(ids).size).toBe(ids.length);
    expect(ids.slice(0, 3)).toEqual(['APN-1001', 'APN-1002', 'APN-1003']);
  });

  it('never leaves a waiting item overdue and never shows real URLs', () => {
    for (const i of seed.incidents.filter((x) => x.stage === 'awaiting')) {
      expect(i.dueAt).toBeGreaterThan(ANCHOR);
    }
    for (const i of seed.incidents) expect(i.evidence.locator.startsWith('evidence://sample/')).toBe(true);
  });

  it('has realistic stage mix', () => {
    const stages = countByStage(seed.incidents);
    expect(stages.awaiting).toBe(76);
    expect(stages.in_review).toBeGreaterThan(0);
    expect(stages.closed).toBeGreaterThan(0);
  });

  it('rng stays in [0,1)', () => {
    const rng = mulberry32(1);
    for (let i = 0; i < 1000; i++) {
      const v = rng();
      expect(v).toBeGreaterThanOrEqual(0);
      expect(v).toBeLessThan(1);
    }
  });
});
