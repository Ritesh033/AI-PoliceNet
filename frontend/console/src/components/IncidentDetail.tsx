import { useEffect, useState, type ReactNode } from 'react';
import type { Incident } from '../types';
import { CATEGORY_LABEL } from '../data/constants';
import { actionLabel, type ReviewAction } from '../state/consoleState';
import { ago, dueLabel, fmtDateTime, fmtPct } from '../lib/format';
import { Card } from './Card';
import { Icon } from './Icon';
import { LaneTag, PriorityBadge, StageBadge } from './Badges';

interface Props {
  incident: Incident | null;
  now: number;
  onAction: (id: string, action: ReviewAction, note: string) => void;
}

export function IncidentDetail({ incident, now, onAction }: Props) {
  const [note, setNote] = useState('');
  const [message, setMessage] = useState('');

  // Switching case clears the draft note and any status message.
  const id = incident?.id;
  useEffect(() => {
    setNote('');
    setMessage('');
  }, [id]);

  if (!incident) {
    return (
      <Card id="detail" title="Case details" subtitle="Select a case from the queue" className="h-full">
        <p className="text-sm text-ink-2">Choose a case ID to see why it was flagged, the preserved evidence and the review options.</p>
      </Card>
    );
  }

  const active = incident.stage === 'awaiting' || incident.stage === 'in_review';
  const due = dueLabel(incident.dueAt, now);
  const social = incident.kind === 'social';
  const act = (action: ReviewAction) => {
    onAction(incident.id, action, note);
    setNote('');
    setMessage(`${actionLabel(action, incident.kind)}. Recorded in the demo audit trail.`);
  };

  return (
    <Card id="detail" title={`${incident.id} · ${incident.title}`} subtitle={CATEGORY_LABEL[incident.category]} className="h-full">
      <div className="mb-3 flex flex-wrap gap-1.5">
        <PriorityBadge priority={incident.priority} />
        <LaneTag lane={incident.lane} />
        <StageBadge stage={incident.stage} />
        {incident.contextRequested && (
          <span className="inline-flex items-center rounded-full border border-line px-2 py-0.5 text-xs font-medium text-ink-2">Context requested</span>
        )}
      </div>

      <p className="text-sm leading-6 text-ink">{incident.summary}</p>

      <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
        <Meta label="Received" value={`${ago(incident.receivedAt, now)} · ${fmtDateTime(incident.receivedAt)}`} />
        <Meta label="Deadline" value={active ? due.text : 'Not applicable'} warn={active && due.overdue} />
        <Meta label="Region" value={`${incident.district}, ${incident.state}`} />
        <Meta label="Source" value={incident.platform ? `${incident.source} · ${incident.platform}` : incident.source} />
      </dl>

      <h3 className="mt-4 text-sm font-semibold text-ink">Why this was flagged</h3>
      <ul className="mt-1.5 list-disc space-y-1 pl-5 text-sm text-ink-2 marker:text-ink-3">
        {incident.signals.map((s) => (
          <li key={s}>{s}</li>
        ))}
      </ul>

      <div className="mt-3 rounded-lg bg-surface-2 p-3">
        <div className="flex items-center justify-between text-sm">
          <span className="font-medium text-ink">Model confidence</span>
          <span className="tnum font-semibold text-ink">{fmtPct(incident.confidence)}</span>
        </div>
        <div
          role="meter"
          aria-label="Model confidence"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={Math.round(incident.confidence * 100)}
          className="mt-1.5 h-2 w-full overflow-hidden rounded-full"
          style={{ background: 'var(--seq-track)' }}
        >
          <div className="h-full rounded-full" style={{ width: `${incident.confidence * 100}%`, background: 'var(--seq)' }} />
        </div>
        <p className="mt-1.5 text-xs leading-5 text-ink-2">
          Confidence is how closely the item matches the flagged category. It is not evidence that an offence occurred.
        </p>
      </div>

      <h3 className="mt-4 text-sm font-semibold text-ink">Evidence</h3>
      {incident.evidence.previewWithheld ? (
        <div className="mt-1.5 flex gap-2 rounded-lg border border-dashed border-axis p-3 text-sm text-ink-2" style={{ borderColor: 'var(--axis)' }}>
          <Icon name="eyeOff" size={18} className="mt-0.5 shrink-0" />
          <p>Preview withheld. Sensitive content is never shown in this console; viewing needs an authorized evidence-room session, which this demo does not include.</p>
        </div>
      ) : (
        <p className="mt-1.5 text-sm text-ink-2">No media is bundled with the demo. A real deployment would open a controlled, access-logged viewer.</p>
      )}
      <dl className="mt-2 space-y-1 text-sm">
        <Meta label="Captured" value={fmtDateTime(incident.evidence.capturedAt)} />
        <Meta label="Sample locator" value={incident.evidence.locator} mono />
        <Meta label="SHA-256 (sample)" value={incident.evidence.hash} mono wrap />
      </dl>

      <h3 className="mt-4 text-sm font-semibold text-ink">Suggested next step</h3>
      <p className="mt-1 text-sm leading-6 text-ink-2">{incident.nextStep}</p>

      <div className="mt-4 rounded-lg border border-line p-3">
        <h3 className="text-sm font-semibold text-ink">Human review</h3>
        {active ? (
          <>
            <label htmlFor="reviewer-note" className="mt-2 block text-sm text-ink-2">
              Reviewer note <span className="text-ink-3">(optional, stored in the audit trail)</span>
            </label>
            <textarea
              id="reviewer-note"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              rows={2}
              maxLength={500}
              className="mt-1 w-full rounded-lg border border-line bg-surface px-3 py-2 text-sm text-ink"
            />
            <div className="mt-2 flex flex-wrap gap-2">
              {incident.stage === 'awaiting' && <ActionButton onClick={() => act('assign')} primary>Assign to me</ActionButton>}
              <ActionButton onClick={() => act('request_context')}>Request more context</ActionButton>
              <ActionButton onClick={() => act('no_action')}>No action</ActionButton>
              <ActionButton onClick={() => act('refer')} primary={incident.stage === 'in_review'}>
                {social ? 'Refer to authorized officer' : 'Route to supervisory authority'}
              </ActionButton>
            </div>
          </>
        ) : (
          <p className="mt-1 text-sm text-ink-2">
            This case is {incident.stage === 'referred' ? 'with an authorized officer' : 'closed'}. No further demo actions are available.
          </p>
        )}
        <p role="status" className="mt-2 min-h-5 text-sm text-ok-text">
          {message}
        </p>
        <p className="mt-1 flex gap-2 text-xs leading-5 text-ink-2">
          <Icon name="info" size={14} className="mt-0.5 shrink-0" />
          <span>
            AI output is advisory. This console does not register an FIR, suspend an officer or remove content. Demo actions change this page only and are not saved.
          </span>
        </p>
      </div>

      <h3 className="mt-4 text-sm font-semibold text-ink">Audit trail</h3>
      <ol className="mt-1.5 space-y-2 border-l border-line pl-4 text-sm">
        {[...incident.history].reverse().map((h, idx) => (
          <li key={`${h.at}-${idx}`} className="relative">
            <span aria-hidden="true" className="absolute -left-[21px] top-1.5 h-2 w-2 rounded-full" style={{ background: 'var(--axis)' }} />
            <p className="text-ink">
              {h.action} <span className="text-ink-2">· {h.actor}</span>
            </p>
            <p className="text-xs text-ink-2">{fmtDateTime(h.at)}</p>
            {h.note && <p className="text-ink-2">“{h.note}”</p>}
          </li>
        ))}
      </ol>
    </Card>
  );
}

function Meta({ label, value, warn, mono, wrap }: { label: string; value: string; warn?: boolean; mono?: boolean; wrap?: boolean }) {
  return (
    <div className="min-w-0">
      <dt className="text-xs text-ink-3">{label}</dt>
      <dd className={`${mono ? 'font-mono text-xs' : 'text-sm'} ${wrap ? 'break-all' : 'break-words'} ${warn ? 'font-medium text-crit' : 'text-ink'}`}>{value}</dd>
    </div>
  );
}

function ActionButton({ children, onClick, primary }: { children: ReactNode; onClick: () => void; primary?: boolean }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`min-h-10 rounded-lg border px-3 text-sm font-medium ${
        primary ? 'border-accent bg-accent text-accent-ink hover:opacity-90' : 'border-line bg-surface text-ink hover:bg-surface-2'
      }`}
    >
      {children}
    </button>
  );
}
