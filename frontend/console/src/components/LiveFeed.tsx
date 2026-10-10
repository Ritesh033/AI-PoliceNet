import type { FeedEvent } from '../types';
import { fmtClock } from '../lib/format';
import { Card } from './Card';
import { Icon, type IconName } from './Icon';

const TONE: Record<FeedEvent['tone'], { icon: IconName; label: string }> = {
  alert: { icon: 'radar', label: 'Alert' },
  queue: { icon: 'clock', label: 'Queued' },
  system: { icon: 'user', label: 'Reviewer' },
};

interface Props {
  events: FeedEvent[];
  live: boolean;
  onToggle: () => void;
}

export function LiveFeed({ events, live, onToggle }: Props) {
  return (
    <Card
      id="feed"
      title="Live activity"
      subtitle="Simulated events generated in your browser"
      className="h-full"
      actions={
        <button
          type="button"
          onClick={onToggle}
          aria-pressed={!live}
          className="inline-flex min-h-9 items-center gap-1.5 rounded-lg border border-line bg-surface px-3 text-sm font-medium text-ink-2 hover:bg-surface-2 hover:text-ink"
        >
          <Icon name={live ? 'pause' : 'play'} />
          {live ? 'Pause' : 'Resume'}
        </button>
      }
    >
      <p className="mb-2 flex items-center gap-2 text-sm text-ink-2">
        <span
          aria-hidden="true"
          className={`h-2.5 w-2.5 rounded-full ${live ? 'live-dot' : ''}`}
          style={{ background: live ? 'var(--s3)' : 'var(--axis)' }}
        />
        {live ? 'Live (simulated)' : 'Paused'}
      </p>
      {/* aria-live stays off: a stream of announcements would be noise. The pause control satisfies WCAG 2.2.2. */}
      <div role="log" aria-live="off" aria-label="Recent activity" className="max-h-[292px] overflow-y-auto pr-1" tabIndex={0}>
        <ul className="divide-y divide-line">
          {events.slice(0, 12).map((e) => (
          <li key={e.id} className="flex gap-2.5 py-2 text-sm">
            <Icon name={TONE[e.tone].icon} className="mt-0.5 shrink-0 text-ink-3" />
            <div className="min-w-0">
              <p className="break-words text-ink">
                <span className="sr-only">{TONE[e.tone].label}: </span>
                {e.text}
              </p>
              <p className="tnum text-xs text-ink-3">{fmtClock(e.at)} IST</p>
            </div>
          </li>
          ))}
        </ul>
      </div>
    </Card>
  );
}
