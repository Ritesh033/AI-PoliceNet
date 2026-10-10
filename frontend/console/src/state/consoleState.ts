import type { AuditEntry, CategoryId, FeedEvent, Incident, Triage } from '../types';
import type { SeedData } from '../data/seed';

export const REVIEWER = 'You (demo reviewer)';
const FEED_LIMIT = 40;

export interface LiveExtras {
  total: number;
  byCategory: Record<CategoryId, number>;
  byTriage: Record<Triage, number>;
}

export interface ConsoleState {
  incidents: Incident[];
  feed: FeedEvent[];
  extras: LiveExtras;
}

export type ReviewAction = 'assign' | 'request_context' | 'no_action' | 'refer';

export type ConsoleAction =
  | { type: 'review'; id: string; action: ReviewAction; at: number; note?: string }
  | { type: 'live'; at: number; event: FeedEvent; category: CategoryId; triage: Triage; incident?: Incident }
  | { type: 'reset'; seed: SeedData };

export function emptyExtras(): LiveExtras {
  return {
    total: 0,
    byCategory: { threat: 0, scam: 0, ncii: 0, hate: 0, manipulated: 0 },
    byTriage: { urgent: 0, review: 0, none: 0 },
  };
}

/** Recent items shown in the feed before any live event arrives. */
function initialFeed(incidents: readonly Incident[]): FeedEvent[] {
  return [...incidents]
    .sort((a, b) => b.receivedAt - a.receivedAt)
    .slice(0, 6)
    .map((i) => ({
      id: `seed-${i.id}`,
      at: i.receivedAt,
      tone: i.stage === 'awaiting' ? ('queue' as const) : ('alert' as const),
      text:
        i.stage === 'awaiting'
          ? `${i.id} queued for human review · ${i.title}`
          : `${i.id} ${i.stage === 'referred' ? 'referred' : 'updated'} · ${i.state}`,
    }));
}

export function initialState(seed: SeedData): ConsoleState {
  return { incidents: seed.incidents, feed: initialFeed(seed.incidents), extras: emptyExtras() };
}

const ACTION_COPY: Record<ReviewAction, { label: string; stage?: Incident['stage'] }> = {
  assign: { label: 'Assigned for review', stage: 'in_review' },
  request_context: { label: 'Requested more context' },
  no_action: { label: 'Closed: no action', stage: 'closed' },
  refer: { label: 'Referred to authorized officer', stage: 'referred' },
};

export function actionLabel(action: ReviewAction, kind: Incident['kind']): string {
  if (action === 'refer' && kind === 'conduct') return 'Routed to supervisory authority';
  return ACTION_COPY[action].label;
}

export function reducer(state: ConsoleState, action: ConsoleAction): ConsoleState {
  switch (action.type) {
    case 'review': {
      const incidents = state.incidents.map((i) => {
        if (i.id !== action.id) return i;
        const copy = ACTION_COPY[action.action];
        const entry: AuditEntry = {
          at: action.at,
          actor: REVIEWER,
          action: actionLabel(action.action, i.kind),
          note: action.note?.trim() || undefined,
        };
        return {
          ...i,
          stage: copy.stage ?? i.stage,
          referredAt: action.action === 'refer' ? action.at : i.referredAt,
          contextRequested: action.action === 'request_context' ? true : i.contextRequested,
          history: [...i.history, entry],
        };
      });
      const target = incidents.find((i) => i.id === action.id);
      const feed: FeedEvent[] = target
        ? [
            {
              id: `act-${action.id}-${action.at}`,
              at: action.at,
              tone: 'system' as const,
              text: `${target.id} · ${actionLabel(action.action, target.kind)} (demo action)`,
            },
            ...state.feed,
          ].slice(0, FEED_LIMIT)
        : state.feed;
      return { ...state, incidents, feed };
    }
    case 'live': {
      const extras: LiveExtras = {
        total: state.extras.total + 1,
        byCategory: {
          ...state.extras.byCategory,
          [action.category]: state.extras.byCategory[action.category] + 1,
        },
        byTriage: { ...state.extras.byTriage, [action.triage]: state.extras.byTriage[action.triage] + 1 },
      };
      return {
        incidents: action.incident ? [...state.incidents, action.incident] : state.incidents,
        feed: [action.event, ...state.feed].slice(0, FEED_LIMIT),
        extras,
      };
    }
    case 'reset':
      return initialState(action.seed);
  }
}
