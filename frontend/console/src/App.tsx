import { useCallback, useEffect, useMemo, useReducer, useRef, useState } from 'react';
import type { Period } from './types';
import { PERIODS } from './data/constants';
import { buildSeed } from './data/seed';
import { initialState, reducer, type ReviewAction } from './state/consoleState';
import { makeLiveTick } from './state/liveTick';
import {
  awaitingByState,
  awaitingCount,
  openComplaints,
  periodStats,
  urgentReferrals,
  withExtras,
} from './state/selectors';
import { fmtInt, fmtPct, dueLabel, waited } from './lib/format';
import { useNow, useReducedMotion, useTheme } from './hooks';
import { DemoBanner, Header, Placeholder, Tabs, type TabDef } from './components/Shell';
import { StatTile } from './components/StatTile';
import { AlertsChart } from './components/AlertsChart';
import { TriagePanel } from './components/TriagePanel';
import { ReviewQueue } from './components/ReviewQueue';
import { IncidentDetail } from './components/IncidentDetail';
import { StateChart } from './components/StateChart';
import { ComplaintsPanel } from './components/ComplaintsPanel';
import { LiveFeed } from './components/LiveFeed';
import { DecisionLayers } from './components/DecisionLayers';
import { Icon } from './components/Icon';

const TABS: readonly TabDef[] = [
  { id: 'overview', label: 'Overview' },
  { id: 'social', label: 'Social media' },
  { id: 'accountability', label: 'Accountability' },
  { id: 'legal', label: 'Legal cases' },
];

const PLANNED = {
  social: {
    title: 'Social media cyber policing',
    module: 'Module A',
    items: [
      'Detect credible threats, targeted harassment, blackmail and suspected non-consensual intimate imagery.',
      'Flag suspected scams, impersonation and manipulated media with an explanation for each alert.',
      'Preserve permitted evidence and source references with timestamps and integrity hashes.',
      'Route high-risk cases to the appropriate authorized cybercrime team.',
    ],
  },
  accountability: {
    title: 'Police and government employee accountability',
    module: 'Module B',
    items: [
      'Accept citizen complaints through web and mobile apps and acknowledge them on a clock.',
      'Review lawfully obtained recordings and transcripts against approved conduct rules.',
      'Route incident reports to an independent supervisory or vigilance authority.',
      'Track deadlines, findings and appeals. Outcomes follow verified findings, not complaint counts.',
    ],
  },
  legal: {
    title: 'AI legal assistant and case tracking',
    module: 'Module C',
    items: [
      'Map complaint facts to potentially applicable provisions for an authorized officer to assess.',
      'Generate draft complaints and evidence inventories. Drafts are never filed automatically.',
      'Show the full history of amendments, approvals and decisions.',
      'Follow BNSS and IT Act procedure, preserving judicial independence and human adjudication.',
    ],
  },
} as const;

const NEXT_PERIOD_WORD: Record<Period, string> = { '24h': 'previous 24 hours', '7d': 'previous 7 days', '30d': 'previous 30 days' };

function numericId(id: string): number {
  return Number(id.replace(/\D/g, '')) || 0;
}

export function App({ simulateLive = true }: { simulateLive?: boolean }) {
  const [theme, toggleTheme] = useTheme();
  const reducedMotion = useReducedMotion();
  const now = useNow(30_000);

  const [seed, setSeed] = useState(() => buildSeed());
  const [state, dispatch] = useReducer(reducer, seed, initialState);
  const [tab, setTab] = useState('overview');
  const [period, setPeriod] = useState<Period>('7d');
  const [live, setLive] = useState(simulateLive);
  const [selectedId, setSelectedId] = useState<string | null>('APN-1001');

  const nextNumber = useRef(Math.max(...seed.incidents.map((i) => numericId(i.id))) + 1);
  const seq = useRef(0);

  useEffect(() => {
    if (!live) return;
    let timer = 0;
    const schedule = () => {
      timer = window.setTimeout(() => {
        const at = Date.now();
        const tick = makeLiveTick(Math.random, at, nextNumber.current, seq.current++);
        if (tick.incident) nextNumber.current += 1;
        dispatch({ type: 'live', at, ...tick });
        schedule();
      }, 2800 + Math.random() * 3200);
    };
    schedule();
    return () => window.clearTimeout(timer);
  }, [live]);

  const onAction = useCallback((id: string, action: ReviewAction, note: string) => {
    dispatch({ type: 'review', id, action, note, at: Date.now() });
  }, []);

  const onReset = useCallback(() => {
    const fresh = buildSeed();
    setSeed(fresh);
    dispatch({ type: 'reset', seed: fresh });
    nextNumber.current = Math.max(...fresh.incidents.map((i) => numericId(i.id))) + 1;
    setSelectedId('APN-1001');
  }, []);

  const stats = useMemo(() => periodStats(seed.series[period], state.extras), [seed, period, state.extras]);
  const buckets = useMemo(() => withExtras(seed.series[period], state.extras), [seed, period, state.extras]);
  const waiting = useMemo(() => awaitingCount(state.incidents), [state.incidents]);
  const referrals = useMemo(() => urgentReferrals(state.incidents, period, now), [state.incidents, period, now]);
  const complaints = useMemo(() => openComplaints(state.incidents), [state.incidents]);
  const byState = useMemo(() => awaitingByState(state.incidents), [state.incidents]);
  const selected = state.incidents.find((i) => i.id === selectedId) ?? null;
  const periodMeta = PERIODS.find((p) => p.id === period)!;

  const alertsDelta = stats.previousTotal > 0 ? (stats.total - stats.previousTotal) / stats.previousTotal : 0;
  const refDiff = referrals.current - referrals.previous;
  const oldestWaiting = waiting.oldest !== null ? waited(waiting.oldest, now) : null;
  const nextDue = useMemo(() => {
    const first = state.incidents
      .filter((i) => i.stage === 'awaiting')
      .sort((a, b) => a.dueAt - b.dueAt)[0];
    return first ? dueLabel(first.dueAt, now).text.toLowerCase() : null;
  }, [state.incidents, now]);

  return (
    <>
      <a
        href="#main"
        className="sr-only-focusable fixed left-3 top-3 z-50 rounded-lg bg-accent px-3 py-2 text-sm font-medium text-accent-ink"
      >
        Skip to main content
      </a>
      <DemoBanner />
      <Header theme={theme} onToggleTheme={toggleTheme} />

      <main id="main" className="mx-auto max-w-[1400px] px-4 pb-10 pt-5 sm:px-6">
        <div className="mb-4 flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-ink">Overview</h1>
            <p className="text-sm text-ink-2">Sample figures · illustrative period · human review required for every action</p>
          </div>
        </div>

        <div className="mb-5 border-b border-line">
          <Tabs tabs={TABS} active={tab} onChange={setTab} />
        </div>

        {tab === 'overview' ? (
          <div role="tabpanel" id="panel-overview" aria-labelledby="tab-overview" className="space-y-4">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
              <div className="flex flex-wrap items-center gap-3">
                <div role="group" aria-label="Reporting period" className="inline-flex rounded-lg border border-line bg-surface p-0.5">
                  {PERIODS.map((p) => (
                    <button
                      key={p.id}
                      type="button"
                      aria-pressed={period === p.id}
                      onClick={() => setPeriod(p.id)}
                      className={`min-h-9 rounded-md px-3.5 text-sm font-medium ${
                        period === p.id ? 'bg-accent text-accent-ink' : 'text-ink-2 hover:bg-surface-2 hover:text-ink'
                      }`}
                    >
                      {p.label}
                    </button>
                  ))}
                </div>
                <button
                  type="button"
                  onClick={onReset}
                  className="inline-flex min-h-9 items-center gap-1.5 rounded-lg border border-line bg-surface px-3 text-sm font-medium text-ink-2 hover:bg-surface-2 hover:text-ink"
                >
                  <Icon name="reset" />
                  Reset demo data
                </button>
              </div>
              <p className="max-w-xl text-sm text-ink-2">
                The period applies to alerts, triage and referrals. Queue, complaints and region figures show current status.
              </p>
            </div>

            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              <StatTile
                id="tile-alerts"
                label="Alerts received"
                value={fmtInt(stats.total)}
                scope="Period"
                caption={`Illustrative · ${periodMeta.long}`}
                delta={{
                  text: `${alertsDelta >= 0 ? '+' : '−'}${fmtPct(Math.abs(alertsDelta), 1)}`,
                  direction: alertsDelta > 0.0005 ? 'up' : alertsDelta < -0.0005 ? 'down' : 'flat',
                  versus: `vs ${NEXT_PERIOD_WORD[period]}`,
                }}
                spark={buckets.map((b) => b.total)}
              />
              <StatTile
                id="tile-awaiting"
                label="Awaiting review"
                value={fmtInt(waiting.count)}
                scope="Current"
                caption={`Human assessment needed${oldestWaiting ? ` · oldest waiting ${oldestWaiting}` : ''}${nextDue ? ` · next ${nextDue}` : ''}`}
              />
              <StatTile
                id="tile-referrals"
                label="Urgent referrals"
                value={fmtInt(referrals.current)}
                scope="Period"
                caption={`Illustrative count · ${periodMeta.long}`}
                delta={{
                  text: `${refDiff >= 0 ? '+' : '−'}${Math.abs(refDiff)}`,
                  direction: refDiff > 0 ? 'up' : refDiff < 0 ? 'down' : 'flat',
                  versus: `vs ${NEXT_PERIOD_WORD[period]}`,
                }}
              />
              <StatTile
                id="tile-complaints"
                label="Open complaints"
                value={fmtInt(complaints.total)}
                scope="Current"
                caption="Illustrative count · conduct complaints against officials, all stages"
              />
            </div>

            <div className="grid gap-4 lg:grid-cols-12">
              <div className="lg:col-span-8 min-w-0">
                <AlertsChart period={period} buckets={buckets} perCategory={stats.perCategory} total={stats.total} reducedMotion={reducedMotion} />
              </div>
              <div className="lg:col-span-4 min-w-0">
                <TriagePanel triage={stats.triage} total={stats.total} periodLabel={periodMeta.long} />
              </div>
            </div>

            <div className="grid gap-4 lg:grid-cols-12">
              <div className="lg:col-span-7 min-w-0">
                <ReviewQueue incidents={state.incidents} selectedId={selectedId} onSelect={setSelectedId} now={now} />
              </div>
              <div className="lg:col-span-5 min-w-0">
                <IncidentDetail incident={selected} now={now} onAction={onAction} />
              </div>
            </div>

            <div className="grid gap-4 lg:grid-cols-3">
              <StateChart rows={byState} reducedMotion={reducedMotion} />
              <ComplaintsPanel total={complaints.total} stages={complaints.stages} />
              <LiveFeed events={state.feed} live={live} onToggle={() => setLive((v) => !v)} />
            </div>

            <DecisionLayers />
          </div>
        ) : (
          <Placeholder id={tab} {...PLANNED[tab as keyof typeof PLANNED]} />
        )}
      </main>

      <footer className="border-t border-line px-4 py-5 text-center text-xs leading-5 text-ink-2 sm:px-6">
        <p>
          AI Policing Net · DEMO build · Sample data is generated locally in your browser. No requests are made to social-media
          platforms or police systems.
        </p>
      </footer>
    </>
  );
}
