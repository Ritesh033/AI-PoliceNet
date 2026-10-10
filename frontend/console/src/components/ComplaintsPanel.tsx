import { COMPLAINT_METRICS } from '../data/constants';
import { fmtInt, fmtPct } from '../lib/format';
import { Card } from './Card';
import { Icon } from './Icon';

interface Props {
  total: number;
  stages: Array<{ id: string; label: string; note: string; value: number }>;
}

export function ComplaintsPanel({ total, stages }: Props) {
  const max = Math.max(...stages.map((s) => s.value), 1);
  const ack = COMPLAINT_METRICS.acknowledgedWithin24h;
  const target = COMPLAINT_METRICS.acknowledgementTarget;
  return (
    <Card id="complaints" title="Open conduct complaints" subtitle={`${fmtInt(total)} open · complaints about police and government employees`} className="h-full">
      <ul className="space-y-2.5">
        {stages.map((s) => (
          <li key={s.id}>
            <div className="flex items-baseline justify-between gap-2 text-sm">
              <span className="text-ink">
                {s.label} <span className="text-ink-3">· {s.note}</span>
              </span>
              <span className="tnum font-semibold text-ink">{fmtInt(s.value)}</span>
            </div>
            <div className="mt-1 h-2 w-full overflow-hidden rounded-full" style={{ background: 'var(--seq-track)' }} aria-hidden="true">
              <div className="h-full rounded-r-[4px]" style={{ width: `${(s.value / max) * 100}%`, background: 'var(--seq)' }} />
            </div>
          </li>
        ))}
      </ul>

      <div className="mt-4 grid grid-cols-2 gap-3 border-t border-line pt-3 text-sm">
        <div>
          <p className="text-ink-2">Past deadline</p>
          <p className="mt-0.5 flex items-center gap-1.5 font-semibold text-ink">
            <Icon name="alert" size={16} className="text-warn-ink" />
            <span className="tnum">{COMPLAINT_METRICS.overdue}</span> investigations
          </p>
        </div>
        <div>
          <p className="text-ink-2">Acknowledged within 24 h</p>
          <p className="tnum mt-0.5 font-semibold text-ink">
            {fmtPct(ack)} <span className="font-normal text-ink-2">· target {fmtPct(target)}</span>
          </p>
          <div
            role="meter"
            aria-label="Complaints acknowledged within 24 hours"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={Math.round(ack * 100)}
            aria-valuetext={`${fmtPct(ack)}, target ${fmtPct(target)}`}
            className="relative mt-1.5 h-2 w-full rounded-full"
            style={{ background: 'var(--seq-track)' }}
          >
            <div className="h-full rounded-full" style={{ width: `${ack * 100}%`, background: 'var(--seq)' }} />
            <span aria-hidden="true" className="absolute -top-1 h-4 w-0.5 rounded" style={{ left: `${target * 100}%`, background: 'var(--ink)' }} />
          </div>
        </div>
      </div>

      <p className="mt-auto flex gap-2 pt-3 text-sm text-ink-2">
        <Icon name="info" className="mt-0.5 shrink-0" />
        Complaint counts do not decide outcomes. Findings follow verified evidence, service rules and appeal rights.
      </p>
    </Card>
  );
}
