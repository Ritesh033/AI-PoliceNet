import { useCallback, useMemo, useState } from 'react';
import { ApiClient, ApiError, normalizeBaseUrl } from '../../api/client';
import { API_ROLES, type ActionMeta, type ApiCase, type ApiRole, type ApiStage } from '../../api/types';
import { dueLabel } from '../../lib/format';
import { Card } from '../Card';
import { Icon } from '../Icon';
import { PriorityBadge } from '../Badges';
import { CaseDetailLive } from './CaseDetailLive';
import { API_STAGE_LABEL } from './labels';

const DEFAULT_URL = 'http://localhost:8100';

type Status = { kind: 'idle' | 'connecting' | 'ok' | 'error'; text: string };

function sortCases(list: ApiCase[]): ApiCase[] {
  const active = (c: ApiCase) => ['received', 'in_review', 'referred', 'inquiry'].includes(c.stage);
  return [...list].sort((a, b) => {
    if (active(a) !== active(b)) return active(a) ? -1 : 1;
    const da = a.decision_due_at ?? '9999';
    const db = b.decision_due_at ?? '9999';
    return da.localeCompare(db) || a.id.localeCompare(b.id);
  });
}

export function LiveCases({ now }: { now: number }) {
  const [url, setUrl] = useState(DEFAULT_URL);
  const [roleId, setRoleId] = useState<ApiRole>('reviewer');
  const [client, setClient] = useState<ApiClient | null>(null);
  const [status, setStatus] = useState<Status>({ kind: 'idle', text: 'Not connected.' });
  const [cases, setCases] = useState<ApiCase[]>([]);
  const [meta, setMeta] = useState<ActionMeta | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [stage, setStage] = useState<'all' | ApiStage>('all');

  const connect = useCallback(async (role: ApiRole, checkHealth: boolean) => {
    const base = normalizeBaseUrl(url);
    if (!base) {
      setStatus({ kind: 'error', text: 'Enter a valid http:// or https:// address.' });
      return;
    }
    const actor = API_ROLES.find((r) => r.id === role)!;
    const next = new ApiClient(base, { id: actor.actorId, role });
    setStatus({ kind: 'connecting', text: 'Connecting…' });
    try {
      let auth = '';
      if (checkHealth) auth = (await next.health()).auth;
      const [m, list] = await Promise.all([next.metaActions(), next.listCases()]);
      setClient(next);
      setMeta(m);
      setCases(sortCases(list));
      setSelectedId((cur) => (cur && list.some((c) => c.id === cur) ? cur : sortCases(list)[0]?.id ?? null));
      setStatus({
        kind: 'ok',
        text: `Connected to ${base} as ${actor.label}${auth ? ` (auth: ${auth})` : ''}. ${list.length} cases.`,
      });
    } catch (e) {
      setClient(null);
      setStatus({ kind: 'error', text: e instanceof ApiError ? e.message : String(e) });
    }
  }, [url]);

  const refresh = useCallback(async () => {
    if (!client) return;
    setCases(sortCases(await client.listCases()));
  }, [client]);

  const visible = useMemo(() => cases.filter((c) => stage === 'all' || c.stage === stage), [cases, stage]);
  const selected = cases.find((c) => c.id === selectedId) ?? null;
  // The role shown and used comes from the client that makes the requests, so the two can never disagree mid-switch.
  const stagesPresent = useMemo(() => [...new Set(cases.map((c) => c.stage))], [cases]);

  return (
    <div className="space-y-4">
      <section aria-labelledby="live-notice-title" className="card p-4 sm:p-5">
        <h2 id="live-notice-title" className="text-base font-semibold text-ink">
          Case core (live API)
        </h2>
        <p className="mt-1 max-w-3xl text-sm leading-6 text-ink-2">
          This tab talks to a case-core API you run yourself (see <code className="font-mono text-xs">backend/case-core</code>). Data
          is invented sample data and sign-in is a demo stub. The Overview tab stays on built-in mock data. Every rule shown
          here is enforced by the server, not this page.
        </p>
        <form
          className="mt-3 flex flex-col gap-3 sm:flex-row sm:items-end"
          onSubmit={(e) => {
            e.preventDefault();
            void connect(roleId, true);
          }}
        >
          <label className="block flex-1 text-sm text-ink-2">
            API address
            <input
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              inputMode="url"
              autoComplete="off"
              spellCheck={false}
              className="mt-1 block min-h-10 w-full rounded-lg border border-line bg-surface px-3 text-sm text-ink"
            />
          </label>
          <label className="block text-sm text-ink-2">
            Act as
            <select
              value={roleId}
              onChange={(e) => {
                const next = e.target.value as ApiRole;
                setRoleId(next);
                if (client) void connect(next, false);
              }}
              className="mt-1 block min-h-10 w-full rounded-lg border border-line bg-surface px-2 text-sm text-ink sm:w-56"
            >
              {API_ROLES.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.label}
                </option>
              ))}
            </select>
          </label>
          <button
            type="submit"
            disabled={status.kind === 'connecting'}
            className="min-h-10 rounded-lg border border-accent bg-accent px-4 text-sm font-medium text-accent-ink hover:opacity-90 disabled:opacity-50"
          >
            {client ? 'Reconnect' : 'Connect'}
          </button>
        </form>
        <p className="mt-2 text-xs text-ink-2">{API_ROLES.find((r) => r.id === roleId)!.blurb}</p>
        <p role={status.kind === 'error' ? 'alert' : 'status'} className={`mt-2 text-sm ${status.kind === 'error' ? 'text-crit' : status.kind === 'ok' ? 'text-ok-text' : 'text-ink-2'}`}>
          {status.text}
        </p>
        {status.kind === 'error' || status.kind === 'idle' ? (
          <p className="mt-1 text-xs text-ink-2">
            Start it with:{' '}
            <code className="font-mono">
              cd backend/case-core &amp;&amp; APN_ENV=demo APN_CORS_ORIGINS=http://localhost:3100 python -m app.demo_seed &amp;&amp; APN_ENV=demo
              APN_CORS_ORIGINS=http://localhost:3100 uvicorn app.main:app --port 8100
            </code>
          </p>
        ) : null}
      </section>

      {client && meta && (
        <div className="grid gap-4 lg:grid-cols-12">
          <div className="min-w-0 lg:col-span-6">
            <Card
              id="live-queue"
              title="Cases"
              subtitle="Temporary flags on clips and conduct complaints · soonest human-decision deadline first"
              className="h-full"
              actions={
                <button
                  type="button"
                  onClick={() => void refresh()}
                  className="inline-flex min-h-9 items-center gap-1.5 rounded-lg border border-line bg-surface px-3 text-sm font-medium text-ink-2 hover:bg-surface-2 hover:text-ink"
                >
                  <Icon name="reset" /> Refresh
                </button>
              }
            >
              <label className="mb-3 flex items-center gap-2 text-sm text-ink-2">
                Stage
                <select
                  value={stage}
                  onChange={(e) => setStage(e.target.value as 'all' | ApiStage)}
                  className="min-h-9 rounded-lg border border-line bg-surface px-2 text-sm text-ink"
                >
                  <option value="all">All ({cases.length})</option>
                  {stagesPresent.map((s) => (
                    <option key={s} value={s}>
                      {API_STAGE_LABEL[s]} ({cases.filter((c) => c.stage === s).length})
                    </option>
                  ))}
                </select>
              </label>
              <div className="overflow-x-auto rounded-lg border border-line">
                <table className="w-full border-collapse text-left text-sm">
                  <caption className="sr-only">Cases from the case-core API. Select a case ID to open it.</caption>
                  <thead className="bg-surface-2 text-ink-2">
                    <tr>
                      <th scope="col" className="px-3 py-2 font-medium">Case</th>
                      <th scope="col" className="px-3 py-2 font-medium">Stage</th>
                    </tr>
                  </thead>
                  <tbody>
                    {visible.length === 0 && (
                      <tr>
                        <td colSpan={2} className="px-3 py-8 text-center text-ink-2">
                          No cases. Seed sample data with <code className="font-mono text-xs">python -m app.demo_seed</code>.
                        </td>
                      </tr>
                    )}
                    {visible.map((c) => {
                      const isSelected = c.id === selectedId;
                      const due = c.decision_due_at ? dueLabel(Date.parse(c.decision_due_at), now) : null;
                      const undecided = ['received', 'in_review', 'referred'].includes(c.stage);
                      return (
                        <tr
                          key={c.id}
                          onClick={() => setSelectedId(c.id)}
                          className={`cursor-pointer border-t border-line align-top ${isSelected ? 'bg-accent-soft' : 'hover:bg-surface-2'}`}
                        >
                          <td className="max-w-[18rem] px-3 py-2.5">
                            <button
                              type="button"
                              aria-current={isSelected ? 'true' : undefined}
                              onClick={(e) => {
                                e.stopPropagation();
                                setSelectedId(c.id);
                              }}
                              className="tnum -ml-1 rounded px-1 font-semibold text-accent-text underline-offset-2 hover:underline"
                            >
                              {c.id}
                            </button>
                            <p className="mt-0.5 text-ink">{c.title}</p>
                            <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
                              <PriorityBadge priority={c.priority} />
                              {c.kind === 'social' && c.context_missing.length > 0 && (
                                <span className="text-xs text-ink-2">context: {c.context_missing.length} to do</span>
                              )}
                            </div>
                          </td>
                          <td className="px-3 py-2.5 text-ink-2">
                            {API_STAGE_LABEL[c.stage]}
                            {due && undecided && (
                              <span className={`mt-1 flex items-center gap-1 text-xs ${due.overdue ? 'font-medium text-crit' : ''}`}>
                                <Icon name="clock" size={12} />
                                {due.text}
                              </span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </Card>
          </div>
          <div className="min-w-0 lg:col-span-6">
            {selected ? (
              <CaseDetailLive item={selected} meta={meta} role={client.actor.role} client={client} now={now} onChanged={refresh} />
            ) : (
              <Card id="live-detail" title="Case details" subtitle="Select a case">
                <p className="text-sm text-ink-2">Choose a case to see its checks, evidence hashes, decisions and ledger.</p>
              </Card>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
