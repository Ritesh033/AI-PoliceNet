import type { Triage } from '../types';
import { TRIAGE } from '../data/constants';
import { fmtInt, fmtPct } from '../lib/format';
import { Card } from './Card';
import { Icon, type IconName } from './Icon';

const VISUAL: Record<Triage, { color: string; icon: IconName }> = {
  urgent: { color: 'var(--crit)', icon: 'alert' },
  review: { color: 'var(--warn)', icon: 'clock' },
  none: { color: 'var(--axis)', icon: 'check' },
};

export function TriagePanel({ triage, total, periodLabel }: { triage: Record<Triage, number>; total: number; periodLabel: string }) {
  return (
    <Card id="triage" title="Triage outcomes" subtitle={`Where alerts went · ${periodLabel}`} className="h-full">
      <div
        className="mb-4 flex h-3 w-full gap-0.5 overflow-hidden rounded-full"
        role="img"
        aria-label={TRIAGE.map((t) => `${t.label}: ${fmtInt(triage[t.id])}`).join(', ')}
      >
        {TRIAGE.map((t) => (
          <span key={t.id} style={{ width: `${(triage[t.id] / Math.max(total, 1)) * 100}%`, background: VISUAL[t.id].color, minWidth: triage[t.id] > 0 ? 6 : 0 }} />
        ))}
      </div>
      <ul className="divide-y divide-line">
        {TRIAGE.map((t) => (
          <li key={t.id} className="flex items-center gap-3 py-2.5">
            <span
              aria-hidden="true"
              className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg"
              style={{ background: `color-mix(in srgb, ${VISUAL[t.id].color} 16%, transparent)` }}
            >
              <Icon name={VISUAL[t.id].icon} size={16} className={t.id === 'urgent' ? 'text-crit' : t.id === 'review' ? 'text-warn-ink' : 'text-ink-3'} />
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-ink">{t.label}</p>
              <p className="text-sm text-ink-2">{t.hint}</p>
            </div>
            <div className="text-right">
              <p className="tnum text-base font-semibold text-ink">{fmtInt(triage[t.id])}</p>
              <p className="tnum text-sm text-ink-2">{fmtPct(triage[t.id] / Math.max(total, 1), 1)}</p>
            </div>
          </li>
        ))}
      </ul>
      <p className="mt-auto flex gap-2 pt-3 text-sm text-ink-2">
        <Icon name="info" className="mt-0.5 shrink-0" />
        Triage is advisory. Only a human reviewer can move a case forward.
      </p>
    </Card>
  );
}
