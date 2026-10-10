import type { Priority, Stage } from '../types';
import { Icon, type IconName } from './Icon';

const PRIORITY: Record<Priority, { label: string; icon: IconName; cls: string }> = {
  urgent: { label: 'Urgent', icon: 'alert', cls: 'bg-crit-soft text-ink border-crit/40' },
  high: { label: 'High', icon: 'arrowUp', cls: 'bg-warn-soft text-ink border-warn/60' },
  routine: { label: 'Routine', icon: 'minus', cls: 'bg-surface-2 text-ink-2 border-line' },
};

const ICON_COLOR: Record<Priority, string> = {
  urgent: 'text-crit',
  high: 'text-warn-ink',
  routine: 'text-ink-3',
};

export function PriorityBadge({ priority }: { priority: Priority }) {
  const p = PRIORITY[priority];
  return (
    <span
      className={`inline-flex items-center gap-1 whitespace-nowrap rounded-full border px-2 py-0.5 text-xs font-medium ${p.cls}`}
    >
      <Icon name={p.icon} size={12} className={ICON_COLOR[priority]} />
      {p.label}
    </span>
  );
}

export const STAGE_LABEL: Record<Stage, string> = {
  awaiting: 'Awaiting review',
  in_review: 'In review',
  referred: 'Referred',
  closed: 'Closed, no action',
};

export function StageBadge({ stage }: { stage: Stage }) {
  const icon: IconName = stage === 'closed' ? 'check' : stage === 'referred' ? 'fileCheck' : stage === 'in_review' ? 'user' : 'clock';
  return (
    <span className="inline-flex items-center gap-1 whitespace-nowrap rounded-full border border-line bg-surface-2 px-2 py-0.5 text-xs font-medium text-ink-2">
      <Icon name={icon} size={12} />
      {STAGE_LABEL[stage]}
    </span>
  );
}

export function LaneTag({ lane }: { lane: string }) {
  return (
    <span className="inline-flex items-center rounded-full border border-accent/30 bg-accent-soft px-2 py-0.5 text-xs font-medium text-accent-text">
      {lane}
    </span>
  );
}
