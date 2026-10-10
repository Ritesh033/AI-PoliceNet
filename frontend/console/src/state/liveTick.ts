import type { CategoryId, FeedEvent, Incident, Priority, Triage } from '../types';
import { CATEGORIES, REGIONS, SOCIAL_TEMPLATES, TRIAGE } from '../data/constants';
import { buildIncident, incidentId } from '../data/seed';
import { between, pick, type Rng } from '../lib/random';

export interface LiveTick {
  event: FeedEvent;
  category: CategoryId;
  triage: Triage;
  incident?: Incident;
}

/** Pure generator for one simulated incoming alert. Nothing here touches the network. */
export function makeLiveTick(rng: Rng, now: number, nextIncidentNumber: number, seq: number): LiveTick {
  const category = weightedCategory(rng);
  const triage = weightedTriage(rng);
  const region = REGIONS[Math.floor(rng() * REGIONS.length)];
  const label = CATEGORIES.find((c) => c.id === category)!.short;
  const id = `live-${now}-${seq}`;

  if (triage === 'none') {
    return {
      category,
      triage,
      event: { id, at: now, tone: 'alert', text: `Auto-triaged, no action · ${label} · ${region.state}` },
    };
  }

  // Review and urgent alerts become queue items; routing to a human is the only automated step.
  const social = SOCIAL_TEMPLATES.filter((t) => t.category === category);
  const template = pick(rng, social);
  const priority: Priority = triage === 'urgent' ? 'urgent' : rng() < 0.3 ? 'high' : 'routine';
  const incident = buildIncident(rng, {
    id: incidentId(nextIncidentNumber),
    template,
    kind: 'social',
    category,
    priority,
    stage: 'awaiting',
    receivedAt: now,
    confidence: between(rng, 0.62, 0.95),
    region: { state: region.state, district: pick(rng, region.districts) },
  });
  const text =
    triage === 'urgent'
      ? `Urgent: ${incident.id} flagged for immediate human review · ${label} · ${region.state}`
      : `${incident.id} queued for human review · ${label} · ${region.state}`;
  return { category, triage, incident, event: { id, at: now, tone: 'queue', text } };
}

function weightedCategory(rng: Rng): CategoryId {
  let roll = rng();
  for (const c of CATEGORIES) {
    roll -= c.share;
    if (roll <= 0) return c.id;
  }
  return CATEGORIES[0].id;
}

function weightedTriage(rng: Rng): Triage {
  // Live urgent alerts are rarer than the period mix so the queue does not jump around while someone reads it.
  const weights: Record<Triage, number> = { urgent: 0.02, review: 0.3, none: 0.68 };
  let roll = rng();
  for (const t of TRIAGE) {
    roll -= weights[t.id];
    if (roll <= 0) return t.id;
  }
  return 'none';
}
