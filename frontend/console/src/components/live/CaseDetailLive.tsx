import { useCallback, useEffect, useState } from 'react';
import { ApiError, type ApiClient } from '../../api/client';
import type { ActionMeta, ApiCase, ApiItem, ApiParty, ApiRole, LedgerRow, VerifyResult } from '../../api/types';
import { API_ROLES } from '../../api/types';
import { dueLabel, fmtDateTime } from '../../lib/format';
import { Card } from '../Card';
import { Icon } from '../Icon';
import { PriorityBadge } from '../Badges';
import {
  ACTION_LABEL, API_STAGE_LABEL, BEHAVIOR_LABEL, CONTEXT_KEYS, DETERMINATION_LABEL, OUTCOME_LABEL, PARTY_ROLE_LABEL,
  SCENARIO_LABEL, SCENARIO_RULE,
} from './labels';

interface Props {
  item: ApiCase;
  meta: ActionMeta;
  role: ApiRole;
  client: ApiClient;
  now: number;
  onChanged: () => Promise<void>;
}

const CONSOLE_ROLES = new Set<string>(API_ROLES.map((r) => r.id));

function roleLabel(id: string): string {
  return API_ROLES.find((r) => r.id === id)?.label ?? id;
}

export function CaseDetailLive({ item, meta, role, client, now, onChanged }: Props) {
  const findings = item.items.filter((i) => i.kind === 'context_finding');
  const evidence = item.items.filter((i) => i.kind === 'evidence');
  const advisories = item.items.filter((i) => i.kind === 'advisory');
  const due = item.decision_due_at ? dueLabel(Date.parse(item.decision_due_at), now) : null;
  const undecided = ['received', 'in_review', 'referred'].includes(item.stage);

  return (
    <Card id="live-detail" title={`${item.id} · ${item.title}`} subtitle={item.category.replace(/_/g, ' ')} className="h-full">
      <div className="mb-3 flex flex-wrap gap-1.5">
        <PriorityBadge priority={item.priority} />
        <span className="inline-flex items-center rounded-full border border-line bg-surface-2 px-2 py-0.5 text-xs font-medium text-ink-2">
          {API_STAGE_LABEL[item.stage]}
        </span>
        {item.dismissal_recommended && (
          <span className="inline-flex items-center gap-1 rounded-full border border-accent/30 bg-accent-soft px-2 py-0.5 text-xs font-medium text-accent-text">
            <Icon name="scale" size={12} /> AI recommends dismissal (court decides)
          </span>
        )}
        {item.sla_breached && undecided && (
          <span className="inline-flex items-center gap-1 rounded-full border border-crit/40 bg-crit-soft px-2 py-0.5 text-xs font-medium text-ink">
            <Icon name="alert" size={12} className="text-crit" /> Missed decision deadline: escalated to a supervisor
          </span>
        )}
      </div>

      <p className="text-sm leading-6 text-ink">{item.summary}</p>

      {(item.behaviors.length > 0 || item.situation.length > 0) && (
        <div className="mt-3 text-sm">
          <p className="text-xs text-ink-3">What the model saw</p>
          <ul className="mt-1 flex flex-wrap gap-1.5" aria-label="Detected behaviours and situation">
            {item.behaviors.map((b) => (
              <li key={`b-${b}`} className="rounded-full border border-line bg-surface-2 px-2 py-0.5 text-xs text-ink">
                {BEHAVIOR_LABEL[b] ?? b}
              </li>
            ))}
            {item.situation.map((s) => (
              <li key={`s-${s}`} className="rounded-full border border-dashed px-2 py-0.5 text-xs text-ink-2" style={{ borderColor: 'var(--axis)' }}>
                {s.replace(/_/g, ' ')}
              </li>
            ))}
          </ul>
        </div>
      )}

      <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
        <Meta label="Opened" value={fmtDateTime(Date.parse(item.created_at))} />
        <Meta
          label="Human decision due"
          value={due ? due.text : 'Not applicable'}
          warn={Boolean(due?.overdue && undecided)}
        />
        {item.referred_to_role && <Meta label="Referred to" value={roleLabel(item.referred_to_role)} />}
        {item.window_closes_at && (
          <Meta label="Response window closes" value={fmtDateTime(Date.parse(item.window_closes_at))} />
        )}
        {item.linked_to && <Meta label="Linked to" value={item.linked_to} />}
      </dl>

      {item.kind === 'social' && <ContextChecklist item={item} findings={findings} />}

      {(item.parties?.length ?? 0) > 0 && <WhoIsWho item={item} />}

      {evidence.length > 0 && (
        <>
          <h3 className="mt-4 text-sm font-semibold text-ink">Evidence (hash only)</h3>
          <ul className="mt-1.5 space-y-2 text-sm">
            {evidence.map((e) => (
              <li key={e.id}>
                <p className="text-ink">
                  {e.label}
                  {e.preview_withheld && (
                    <span className="ml-2 inline-flex items-center gap-1 text-xs text-ink-2">
                      <Icon name="eyeOff" size={12} /> preview withheld
                    </span>
                  )}
                </p>
                <p className="break-all font-mono text-xs text-ink-2">{e.sha256}</p>
              </li>
            ))}
          </ul>
        </>
      )}

      {advisories.length > 0 && (
        <>
          <h3 className="mt-4 text-sm font-semibold text-ink">AI advice (non-binding)</h3>
          <ul className="mt-1.5 space-y-1 text-sm text-ink-2">
            {advisories.map((a) => (
              <li key={a.id}>
                {a.label}
                {a.description && <span className="text-ink-3"> · {a.description}</span>}
              </li>
            ))}
          </ul>
        </>
      )}

      <ActionPanel item={item} meta={meta} role={role} client={client} onChanged={onChanged} />
      <LedgerPanel item={item} role={role} client={client} />

      <p className="mt-4 flex gap-2 text-xs leading-5 text-ink-2">
        <Icon name="info" size={14} className="mt-0.5 shrink-0" />
        <span>{item.ai_notice}</span>
      </p>
    </Card>
  );
}

function WhoIsWho({ item }: { item: ApiCase }) {
  const parties = item.parties ?? [];
  return (
    <>
      <h3 className="mt-4 text-sm font-semibold text-ink">Who is who (proposed by the AI, decided by an officer)</h3>
      {SCENARIO_RULE[item.scenario] && (
        <p className="mt-1 text-xs leading-5 text-ink-2">
          <span className="font-medium text-ink">{SCENARIO_LABEL[item.scenario]}.</span> {SCENARIO_RULE[item.scenario]}
        </p>
      )}
      <ul className="mt-1.5 space-y-1.5 text-sm" aria-label="Parties">
        {parties.map((p: ApiParty) => (
          <li key={`${p.ref}-${p.role}`} className="flex flex-wrap items-baseline gap-x-2">
            <span className="font-mono text-xs text-ink-2">{p.ref}</span>
            <span className="text-ink">{PARTY_ROLE_LABEL[p.role] ?? p.role}</span>
            <span
              className={`rounded-full border px-2 py-0.5 text-xs font-medium ${
                p.determination === 'subject'
                  ? 'border-crit/40 bg-crit-soft text-ink'
                  : p.determination === 'victim'
                    ? 'border-accent/30 bg-accent-soft text-accent-text'
                    : 'border-line bg-surface-2 text-ink-2'
              }`}
            >
              {p.determination ? DETERMINATION_LABEL[p.determination] : 'Not yet decided'}
            </span>
          </li>
        ))}
      </ul>
    </>
  );
}

function ContextChecklist({ item, findings }: { item: ApiCase; findings: ApiItem[] }) {
  const latest = (key: string) => [...findings].reverse().find((f) => f.label === key);
  const acknowledged = item.checks.includes('context');
  return (
    <>
      <h3 className="mt-4 text-sm font-semibold text-ink">Full-context check before any referral</h3>
      <ul className="mt-1.5 space-y-1.5 text-sm">
        {CONTEXT_KEYS.map(({ key, label }) => {
          const f = latest(key);
          return (
            <li key={key} className="flex items-start gap-2">
              <Icon
                name={!f ? 'clock' : f.outcome === 'undermines_flag' ? 'alert' : 'check'}
                size={16}
                className={`mt-0.5 shrink-0 ${f?.outcome === 'undermines_flag' ? 'text-warn-ink' : 'text-ink-3'}`}
              />
              <span className="min-w-0">
                <span className="text-ink">{label}: </span>
                <span className="text-ink-2">
                  {f ? `${OUTCOME_LABEL[f.outcome ?? 'inconclusive']}. ${f.description}` : 'Not yet researched'}
                </span>
              </span>
            </li>
          );
        })}
        <li className="flex items-start gap-2">
          <Icon name={acknowledged ? 'check' : 'user'} size={16} className="mt-0.5 shrink-0 text-ink-3" />
          <span className="text-ink">
            Human acknowledgement: <span className="text-ink-2">{acknowledged ? 'recorded' : 'not yet recorded'}</span>
          </span>
        </li>
      </ul>
    </>
  );
}

function ActionPanel({ item, meta, role, client, onChanged }: Omit<Props, 'now'>) {
  const [selected, setSelected] = useState<string | null>(null);
  const [note, setNote] = useState('');
  const [check, setCheck] = useState('');
  const [linkTo, setLinkTo] = useState('');
  const [partyRef, setPartyRef] = useState('');
  const [partyRole, setPartyRole] = useState('');
  const [determination, setDetermination] = useState('');
  const [legalBasis, setLegalBasis] = useState('');
  const [pkg, setPkg] = useState<{ link: string; text: string } | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);

  // A different case resets the form.
  useEffect(() => {
    setSelected(null);
    setNote('');
    setCheck('');
    setLinkTo('');
    setPartyRef('');
    setPartyRole('');
    setDetermination('');
    setLegalBasis('');
    setPkg(null);
    setError(null);
    setMessage('');
  }, [item.id]);

  const available = Object.entries(meta.actions)
    .filter(([name, spec]) => (name === 'resolve_appeal' ? item.appeal_open : spec.from_stages.includes(item.stage)))
    .filter(([, spec]) => spec.roles.some((r) => CONSOLE_ROLES.has(r)));
  const spec = selected ? meta.actions[selected] : null;

  const submit = async () => {
    if (!selected || !spec) return;
    setBusy(true);
    setError(null);
    setMessage('');
    try {
      const has = (name: string) => spec.params.includes(name);
      const updated = await client.act(item.id, {
        action: selected,
        note: note || undefined,
        check: has('check') ? check || undefined : undefined,
        link_to: has('link_to') ? linkTo || undefined : undefined,
        party_ref: has('party_ref') ? partyRef || undefined : undefined,
        party_role: has('party_role') ? partyRole || undefined : undefined,
        determination: has('determination') ? determination || undefined : undefined,
        legal_basis: has('legal_basis') ? legalBasis || undefined : undefined,
      });
      if (updated.issued_response_token && updated.issued_notice_text) {
        setPkg({ link: `/public/responses/${updated.issued_response_token}`, text: updated.issued_notice_text });
      }
      setMessage(`${ACTION_LABEL[selected] ?? selected}: recorded in the ledger.`);
      setNote('');
      setSelected(null);
      await onChanged();
    } catch (e) {
      setError(e instanceof ApiError ? e : new ApiError(0, 'unknown', String(e)));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mt-4 rounded-lg border border-line p-3">
      <h3 className="text-sm font-semibold text-ink">Human decisions</h3>
      {available.length === 0 ? (
        <p className="mt-1 text-sm text-ink-2">No actions are available at this stage.</p>
      ) : (
        <>
          <p className="mt-1 text-xs leading-5 text-ink-2">
            Every step valid at this stage is shown. The server decides who may take it, so choose a step the current role
            should not take to see it refused.
          </p>
          <div role="group" aria-label="Available actions" className="mt-2 flex flex-wrap gap-1.5">
            {available.map(([name]) => (
              <button
                key={name}
                type="button"
                aria-pressed={selected === name}
                onClick={() => {
                  setSelected(name);
                  setError(null);
                  setMessage('');
                }}
                className={`min-h-9 rounded-lg border px-3 text-sm font-medium ${
                  selected === name ? 'border-accent bg-accent text-accent-ink' : 'border-line bg-surface text-ink hover:bg-surface-2'
                }`}
              >
                {ACTION_LABEL[name] ?? name}
              </button>
            ))}
          </div>

          {selected && spec && (
            <form
              className="mt-3 space-y-2"
              onSubmit={(e) => {
                e.preventDefault();
                void submit();
              }}
            >
              <p className="text-xs text-ink-2">
                Expected role: <strong className="text-ink">{spec.roles.map(roleLabel).join(' or ')}</strong>
                {!spec.roles.includes(role) && <span> (you are acting as {roleLabel(role)})</span>}
              </p>
              {spec.params.includes('check') && (
                <label className="block text-sm text-ink-2">
                  Check
                  <select
                    value={check}
                    onChange={(e) => setCheck(e.target.value)}
                    className="mt-1 block min-h-9 w-full rounded-lg border border-line bg-surface px-2 text-sm text-ink"
                  >
                    <option value="">Choose a check</option>
                    {meta.checks.map((c) => (
                      <option key={c} value={c}>
                        {c.replace(/_/g, ' ')}
                      </option>
                    ))}
                  </select>
                </label>
              )}
              {spec.params.includes('party_ref') && (item.parties?.length ?? 0) > 0 && (
                <label className="block text-sm text-ink-2">
                  Party
                  <select
                    value={partyRef}
                    onChange={(e) => {
                      setPartyRef(e.target.value);
                      setPartyRole('');
                    }}
                    className="mt-1 block min-h-9 w-full rounded-lg border border-line bg-surface px-2 text-sm text-ink"
                  >
                    <option value="">Choose a party</option>
                    {[...new Set((item.parties ?? []).map((p) => p.ref))].map((ref) => (
                      <option key={ref} value={ref}>
                        {ref}
                      </option>
                    ))}
                  </select>
                </label>
              )}
              {spec.params.includes('party_role') && (
                <label className="block text-sm text-ink-2">
                  Role being decided
                  <select
                    value={partyRole}
                    onChange={(e) => setPartyRole(e.target.value)}
                    className="mt-1 block min-h-9 w-full rounded-lg border border-line bg-surface px-2 text-sm text-ink"
                  >
                    <option value="">Choose a role</option>
                    {(item.parties ?? [])
                      .filter((p) => p.ref === partyRef)
                      .map((p) => (
                        <option key={p.role} value={p.role}>
                          {PARTY_ROLE_LABEL[p.role] ?? p.role}
                        </option>
                      ))}
                  </select>
                </label>
              )}
              {spec.params.includes('determination') && (
                <label className="block text-sm text-ink-2">
                  Decision
                  <select
                    value={determination}
                    onChange={(e) => setDetermination(e.target.value)}
                    className="mt-1 block min-h-9 w-full rounded-lg border border-line bg-surface px-2 text-sm text-ink"
                  >
                    <option value="">Choose</option>
                    {Object.entries(DETERMINATION_LABEL).map(([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ))}
                  </select>
                </label>
              )}
              {spec.params.includes('legal_basis') && (
                <label className="block text-sm text-ink-2">
                  Legal basis <span className="text-ink">(required)</span>
                  <input
                    value={legalBasis}
                    onChange={(e) => setLegalBasis(e.target.value)}
                    placeholder="Notice or order reference"
                    className="mt-1 block min-h-9 w-full rounded-lg border border-line bg-surface px-3 text-sm text-ink"
                  />
                </label>
              )}
              {spec.params.includes('link_to') && (
                <label className="block text-sm text-ink-2">
                  Existing case to add this information to
                  <input
                    value={linkTo}
                    onChange={(e) => setLinkTo(e.target.value)}
                    placeholder="APN-1007"
                    className="mt-1 block min-h-9 w-full rounded-lg border border-line bg-surface px-3 text-sm text-ink"
                  />
                </label>
              )}
              <label className="block text-sm text-ink-2">
                Written reason {spec.note_required ? <span className="text-ink">(required)</span> : <span className="text-ink-3">(optional)</span>}
                <textarea
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  rows={2}
                  maxLength={500}
                  className="mt-1 block w-full rounded-lg border border-line bg-surface px-3 py-2 text-sm text-ink"
                />
              </label>
              <button
                type="submit"
                disabled={busy}
                className="min-h-10 rounded-lg border border-accent bg-accent px-4 text-sm font-medium text-accent-ink hover:opacity-90 disabled:opacity-50"
              >
                {busy ? 'Submitting…' : `Submit: ${ACTION_LABEL[selected] ?? selected}`}
              </button>
            </form>
          )}
        </>
      )}
      {pkg && (
        <div className="mt-3 rounded-lg border border-accent/30 bg-accent-soft p-3">
          <p className="text-sm font-semibold text-ink">Notice package (shown once)</p>
          <p className="mt-1 text-xs leading-5 text-ink-2">
            This platform never sends messages or looks anyone up. Deliver this notice through a lawful channel and record that you
            did. The private response link works for anyone who holds it, with no login. It is not stored and cannot be shown again.
          </p>
          <p className="mt-2 break-all font-mono text-xs text-ink">{pkg.link}</p>
          <pre
            tabIndex={0}
            aria-label="Notice text"
            className="mt-2 max-h-56 overflow-auto whitespace-pre-wrap rounded bg-surface p-2 text-xs leading-5 text-ink"
          >
            {pkg.text}
          </pre>
        </div>
      )}
      {error && (
        <p role="alert" className="mt-3 flex gap-2 rounded-lg border border-crit/40 bg-crit-soft p-2.5 text-sm text-ink">
          <Icon name="alert" size={16} className="mt-0.5 shrink-0 text-crit" />
          <span>
            <strong className="font-semibold">Refused by the server.</strong> {error.message}
            <span className="block text-xs text-ink-2">
              {error.status ? `HTTP ${error.status} · ` : ''}
              {error.code}
            </span>
          </span>
        </p>
      )}
      <p role="status" className="mt-2 min-h-5 text-sm text-ok-text">
        {message}
      </p>
    </div>
  );
}

function LedgerPanel({ item, role, client }: Pick<Props, 'item' | 'role' | 'client'>) {
  const allowed = role === 'auditor' || role === 'judicial_authority';
  const [rows, setRows] = useState<LedgerRow[]>([]);
  const [verify, setVerify] = useState<VerifyResult | null>(null);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    try {
      setRows(await client.ledger(item.id));
      setError('');
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    }
  }, [client, item.id]);

  // Reload after every change to the case.
  useEffect(() => {
    if (allowed) void load();
  }, [allowed, load, item.updated_at, item.items.length]);

  const runVerify = async () => {
    try {
      setVerify(await client.verify());
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    }
  };

  return (
    <div className="mt-4">
      <h3 className="text-sm font-semibold text-ink">Audit ledger</h3>
      {!allowed ? (
        <p className="mt-1 text-sm text-ink-2">The hash-chained ledger is readable by auditors and judicial authorities. Switch role to view it.</p>
      ) : (
        <>
          <div className="mt-1.5 flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => void runVerify()}
              className="min-h-9 rounded-lg border border-line bg-surface px-3 text-sm font-medium text-ink-2 hover:bg-surface-2 hover:text-ink"
            >
              Verify ledger integrity
            </button>
            {verify && (
              <p role="status" className={`text-sm ${verify.chain_valid && verify.projection_consistent ? 'text-ok-text' : 'font-medium text-crit'}`}>
                {verify.chain_valid && verify.projection_consistent
                  ? `Chain valid: ${verify.entries_checked} entries checked, case states match the ledger.`
                  : `Problem: ${verify.reason ?? verify.projection_problems.join('; ')} (first bad entry ${verify.first_bad_seq ?? 'n/a'})`}
              </p>
            )}
          </div>
          {error && <p role="alert" className="mt-2 text-sm text-crit">{error}</p>}
          <ol className="mt-2 max-h-56 space-y-1.5 overflow-y-auto border-l border-line pl-4 text-sm" tabIndex={0} aria-label="Ledger entries for this case">
            {rows.map((r) => (
              <li key={r.seq} className="relative">
                <span aria-hidden="true" className="absolute -left-[21px] top-1.5 h-2 w-2 rounded-full" style={{ background: 'var(--axis)' }} />
                <p className="text-ink">
                  <span className="tnum text-ink-3">#{r.seq}</span> {r.action}{' '}
                  <span className="text-ink-2">
                    · {roleLabel(r.actor_role)} ({r.actor_kind})
                  </span>
                </p>
                <p className="text-xs text-ink-3">{fmtDateTime(Date.parse(r.ts))}</p>
              </li>
            ))}
          </ol>
        </>
      )}
    </div>
  );
}

function Meta({ label, value, warn }: { label: string; value: string; warn?: boolean }) {
  return (
    <div className="min-w-0">
      <dt className="text-xs text-ink-3">{label}</dt>
      <dd className={`break-words text-sm ${warn ? 'font-medium text-crit' : 'text-ink'}`}>{value}</dd>
    </div>
  );
}
