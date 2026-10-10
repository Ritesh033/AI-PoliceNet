import type {
  AuditEntry,
  Bucket,
  CategoryId,
  Incident,
  IncidentCategory,
  Period,
  PeriodSeries,
  Priority,
  Stage,
} from '../types';
import {
  CATEGORIES,
  CONDUCT_TEMPLATES,
  PLATFORMS,
  REGIONS,
  SLA_MS,
  SOCIAL_TEMPLATES,
  type ConductTemplate,
  type IncidentTemplate,
} from './constants';
import { allocate, between, hex, mulberry32, pick, shuffle, type Rng } from '../lib/random';
import { fmtDayLabel, fmtHourLabel, fmtWeekdayLabel, istHour, TIME } from '../lib/format';

/** Targets taken from the dashboard prototype. The generator builds data that reconciles with them exactly. */
export const TARGETS = {
  alerts7d: 1284,
  awaitingReview: 76,
  awaitingSocial: 58,
  awaitingConduct: 18,
  urgentReferrals7d: 12,
  openComplaints: 143,
} as const;

const DAYS = 60;
const AI_ACTOR = 'AI triage (demo model)';

export interface SeedData {
  anchor: number;
  series: Record<Period, PeriodSeries>;
  incidents: Incident[];
}

export function incidentId(n: number): string {
  return `APN-${String(n).padStart(4, '0')}`;
}

function emptyCounts(): Record<CategoryId, number> {
  return { threat: 0, scam: 0, ncii: 0, hate: 0, manipulated: 0 };
}

const sum = (xs: readonly number[]) => xs.reduce((a, b) => a + b, 0);

/* ----------------------------- alert time series ----------------------------- */

function buildDaily(anchor: number, rng: Rng): Bucket[] {
  // Raw daily volume with a weekly rhythm and gentle upward drift, oldest first.
  const raw = Array.from({ length: DAYS }, (_, d) => {
    const weekly = 1 + 0.12 * Math.sin((d / 7) * 2 * Math.PI);
    return 143 * weekly * (1 + 0.005 * d) * between(rng, 0.92, 1.08);
  });
  // Force the most recent 7 days to the prototype's 1,284 exactly.
  const lastSeven = allocate(TARGETS.alerts7d, raw.slice(-7));
  const totals = [...raw.slice(0, DAYS - 7).map(Math.round), ...lastSeven];

  return totals.map((total, d) => {
    const start = anchor - (DAYS - d) * TIME.DAY;
    const weights = CATEGORIES.map((c) => c.share * between(rng, 0.8, 1.2));
    const parts = allocate(total, weights);
    const counts = emptyCounts();
    CATEGORIES.forEach((c, i) => (counts[c.id] = parts[i]));
    return { start, label: '', counts, total };
  });
}

function buildHourly(anchor: number, today: Bucket, rng: Rng): Bucket[] {
  const hours = Array.from({ length: 24 }, (_, h) => anchor - (24 - h) * TIME.HOUR);
  const diurnal = hours.map((start) => 1 + 0.6 * Math.sin(((istHour(start) - 14) / 24) * 2 * Math.PI));
  const perCategory = CATEGORIES.map((c) =>
    allocate(
      today.counts[c.id],
      diurnal.map((w) => w * between(rng, 0.85, 1.15)),
    ),
  );
  return hours.map((start, h) => {
    const counts = emptyCounts();
    CATEGORIES.forEach((c, i) => (counts[c.id] = perCategory[i][h]));
    return { start, label: fmtHourLabel(start), counts, total: sum(Object.values(counts)) };
  });
}

function buildSeries(anchor: number, rng: Rng): Record<Period, PeriodSeries> {
  const daily = buildDaily(anchor, rng);
  const sevenDay = daily.slice(-7).map((b) => ({ ...b, label: fmtWeekdayLabel(b.start) }));
  const thirtyDay = daily.slice(-30).map((b) => ({ ...b, label: fmtDayLabel(b.start) }));
  const total = (bs: readonly Bucket[]) => sum(bs.map((b) => b.total));
  return {
    '24h': { buckets: buildHourly(anchor, daily[DAYS - 1], rng), previousTotal: daily[DAYS - 2].total },
    '7d': { buckets: sevenDay, previousTotal: total(daily.slice(-14, -7)) },
    '30d': { buckets: thirtyDay, previousTotal: total(daily.slice(-60, -30)) },
  };
}

/* -------------------------------- incidents --------------------------------- */

function makeEvidence(rng: Rng, id: string, capturedAt: number, sensitive: boolean) {
  return {
    hash: hex(rng, 64),
    capturedAt,
    locator: `evidence://sample/${id.toLowerCase()}/v1`,
    previewWithheld: sensitive,
  };
}

function initialHistory(rng: Rng, receivedAt: number, evidenceAt: number): AuditEntry[] {
  return [
    { at: receivedAt, actor: AI_ACTOR, action: 'Alert created and triaged', note: `Model confidence recorded.` },
    { at: evidenceAt, actor: 'Evidence service (demo)', action: 'Item preserved and SHA-256 recorded' },
  ].map((e) => ({ ...e, at: e.at + Math.floor(rng() * 2000) }));
}

interface Draft {
  id: string;
  template: IncidentTemplate | ConductTemplate;
  kind: 'social' | 'conduct';
  category: IncidentCategory;
  priority: Priority;
  stage: Stage;
  receivedAt: number;
  referredAt?: number;
  confidence: number;
  region?: { state: string; district: string };
}

function regionFor(rng: Rng): { state: string; district: string } {
  const total = sum(REGIONS.map((r) => r.weight));
  let roll = rng() * total;
  for (const r of REGIONS) {
    roll -= r.weight;
    if (roll <= 0) return { state: r.state, district: pick(rng, r.districts) };
  }
  const last = REGIONS[REGIONS.length - 1];
  return { state: last.state, district: last.districts[0] };
}

export function buildIncident(rng: Rng, d: Draft): Incident {
  const region = d.region ?? regionFor(rng);
  const isSocial = d.kind === 'social';
  const social = d.template as IncidentTemplate;
  const sensitive = isSocial && Boolean(social.sensitive);
  const evidenceAt = d.receivedAt + 1000;
  return {
    id: d.id,
    kind: d.kind,
    category: d.category,
    title: d.template.title,
    summary: d.template.summary,
    priority: d.priority,
    lane: isSocial ? social.lane : 'Supervisor review',
    stage: d.stage,
    confidence: d.confidence,
    source: pick(rng, d.template.sources),
    platform: isSocial ? pick(rng, PLATFORMS) : undefined,
    state: region.state,
    district: region.district,
    receivedAt: d.receivedAt,
    dueAt: d.receivedAt + SLA_MS[d.priority],
    referredAt: d.referredAt,
    signals: d.template.signals,
    evidence: makeEvidence(rng, d.id, evidenceAt, sensitive),
    nextStep: d.template.nextStep,
    history: initialHistory(rng, d.receivedAt, evidenceAt),
  };
}

function socialTemplateFor(rng: Rng): IncidentTemplate {
  // Weight templates by their category's share so the queue mirrors the alert mix.
  const weights = SOCIAL_TEMPLATES.map((t) => CATEGORIES.find((c) => c.id === t.category)?.share ?? 0.1);
  const total = sum(weights);
  let roll = rng() * total;
  for (let i = 0; i < SOCIAL_TEMPLATES.length; i++) {
    roll -= weights[i];
    if (roll <= 0) return SOCIAL_TEMPLATES[i];
  }
  return SOCIAL_TEMPLATES[0];
}

/** Place `count` timestamps uniformly between `from` and `to` (ms before the anchor). */
function spread(rng: Rng, anchor: number, count: number, fromAgo: number, toAgo: number): number[] {
  return Array.from({ length: count }, () => anchor - between(rng, toAgo, fromAgo)).sort((a, b) => a - b);
}

function buildIncidents(anchor: number, rng: Rng): Incident[] {
  const incidents: Incident[] = [];
  const { MIN, HOUR, DAY } = TIME;

  /* Awaiting review: three featured items from the prototype, then generated ones. */
  const featured: Draft[] = [
    {
      id: 'APN-1001',
      template: SOCIAL_TEMPLATES[0],
      kind: 'social',
      category: 'threat',
      priority: 'urgent',
      stage: 'awaiting',
      receivedAt: anchor - 42 * MIN,
      confidence: 0.87,
      region: { state: 'Maharashtra', district: 'Pune' },
    },
    {
      id: 'APN-1002',
      template: SOCIAL_TEMPLATES[3],
      kind: 'social',
      category: 'ncii',
      priority: 'high',
      stage: 'awaiting',
      receivedAt: anchor - 22 * HOUR - 10 * MIN,
      confidence: 0.91,
      region: { state: 'Uttar Pradesh', district: 'Lucknow' },
    },
    {
      id: 'APN-1003',
      template: CONDUCT_TEMPLATES[0],
      kind: 'conduct',
      category: 'conduct',
      priority: 'high',
      stage: 'awaiting',
      receivedAt: anchor - 21 * HOUR - 5 * MIN,
      confidence: 0.84,
      region: { state: 'Karnataka', district: 'Bengaluru Urban' },
    },
  ];

  // Remaining awaiting: 56 social + 17 conduct. 19 more "high", 54 "routine"; no other urgent items wait,
  // because urgent threats are picked up immediately. All are received late enough that nothing is overdue
  // and the three featured items stay first when sorted by deadline.
  const kinds = shuffle<'social' | 'conduct'>(rng, [
    ...Array<'social'>(TARGETS.awaitingSocial - 2).fill('social'),
    ...Array<'conduct'>(TARGETS.awaitingConduct - 1).fill('conduct'),
  ]);
  const priorities = shuffle<Priority>(rng, [
    ...Array<Priority>(19).fill('high'),
    ...Array<Priority>(kinds.length - 19).fill('routine'),
  ]);
  const generated: Draft[] = kinds.map((kind, i) => {
    const priority = priorities[i];
    const receivedAgo = priority === 'high' ? between(rng, 20 * MIN, 17 * HOUR) : between(rng, 30 * MIN, 38 * HOUR);
    const social = kind === 'social';
    const template = social ? socialTemplateFor(rng) : pick(rng, CONDUCT_TEMPLATES);
    return {
      id: '',
      template,
      kind,
      category: social ? (template as IncidentTemplate).category : 'conduct',
      priority,
      stage: 'awaiting',
      receivedAt: anchor - receivedAgo,
      confidence: between(rng, 0.55, 0.94),
    };
  });
  generated.sort((a, b) => a.receivedAt - b.receivedAt).forEach((d, i) => (d.id = incidentId(1004 + i)));
  [...featured, ...generated].forEach((d) => incidents.push(buildIncident(rng, d)));

  /* Earlier activity: in review, referred (urgent), closed. IDs run up to APN-1000. */
  const earlier: Draft[] = [];
  const add = (stage: Stage, receivedTimes: number[], priority: Priority, referred: boolean) => {
    receivedTimes.forEach((receivedAt) => {
      const template = socialTemplateFor(rng);
      earlier.push({
        id: '',
        template,
        kind: 'social',
        category: template.category,
        priority,
        stage,
        receivedAt,
        referredAt: referred ? receivedAt + between(rng, 5 * MIN, 50 * MIN) : undefined,
        confidence: between(rng, 0.6, 0.97),
      });
    });
  };

  // Urgent referrals by window (ms ago): exactly 12 in the last 7 days, 2 of them in the last 24 hours.
  // Referral times fall inside each window; incidents were received shortly before being referred.
  const referralWindows: Array<[count: number, fromAgo: number, toAgo: number]> = [
    [2, 22 * HOUR, 1 * HOUR],
    [3, 2 * DAY - HOUR, 25 * HOUR],
    [7, 7 * DAY - HOUR, 2 * DAY + HOUR],
    [9, 14 * DAY - HOUR, 7 * DAY + HOUR],
    [20, 30 * DAY - HOUR, 14 * DAY + HOUR],
    [36, 59 * DAY, 31 * DAY],
  ];
  referralWindows.forEach(([count, fromAgo, toAgo]) =>
    add('referred', spread(rng, anchor, count, fromAgo, toAgo), 'urgent', true),
  );
  add('in_review', spread(rng, anchor, 11, 3 * DAY, 4 * HOUR), 'high', false);
  add('in_review', spread(rng, anchor, 3, 3 * DAY, 4 * HOUR), 'routine', false);
  add('closed', spread(rng, anchor, 40, 25 * DAY, 2 * HOUR), 'routine', false);

  // A few in-review / closed items are conduct complaints so every stage shows both kinds.
  const conductOverride = (stage: Stage, count: number) => {
    let n = 0;
    for (const d of earlier) {
      if (d.stage === stage && n < count) {
        const template = pick(rng, CONDUCT_TEMPLATES);
        d.template = template;
        d.kind = 'conduct';
        d.category = 'conduct';
        n += 1;
      }
    }
  };
  conductOverride('in_review', 2);
  conductOverride('closed', 5);

  earlier.sort((a, b) => a.receivedAt - b.receivedAt).forEach((d, i) => (d.id = incidentId(1001 - earlier.length + i)));
  earlier.forEach((d) => {
    const incident = buildIncident(rng, d);
    // Sample history for items that have already moved on.
    if (d.stage === 'in_review') {
      incident.history.push({ at: d.receivedAt + 40 * MIN, actor: 'Reviewer (sample)', action: 'Assigned for review' });
    }
    if (d.stage === 'referred' && d.referredAt) {
      incident.history.push({
        at: d.referredAt,
        actor: 'Reviewer (sample)',
        action: 'Referred to authorized officer',
        note: 'Context verified by a human reviewer.',
      });
    }
    if (d.stage === 'closed') {
      incident.history.push({
        at: d.receivedAt + 6 * HOUR,
        actor: 'Reviewer (sample)',
        action: 'Closed: no action',
        note: 'Context did not support a referral.',
      });
    }
    incidents.push(incident);
  });

  return incidents;
}

export function buildSeed(anchor: number = Date.now(), seed = 20260711): SeedData {
  const rng = mulberry32(seed);
  const rounded = Math.floor(anchor / TIME.MIN) * TIME.MIN;
  return {
    anchor: rounded,
    series: buildSeries(rounded, rng),
    incidents: buildIncidents(rounded, rng),
  };
}
