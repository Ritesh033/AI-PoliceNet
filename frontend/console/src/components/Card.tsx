import type { ReactNode } from 'react';
import { Icon } from './Icon';

interface CardProps {
  id: string;
  title: string;
  subtitle?: string;
  actions?: ReactNode;
  className?: string;
  children: ReactNode;
}

export function Card({ id, title, subtitle, actions, className = '', children }: CardProps) {
  return (
    <section aria-labelledby={`${id}-title`} className={`card flex min-w-0 flex-col p-4 sm:p-5 ${className}`}>
      <div className="mb-3 flex flex-wrap items-start justify-between gap-x-4 gap-y-2">
        <div className="min-w-0">
          <h2 id={`${id}-title`} className="text-base font-semibold leading-6 text-ink">
            {title}
          </h2>
          {subtitle && <p className="text-sm leading-5 text-ink-2">{subtitle}</p>}
        </div>
        {actions}
      </div>
      {children}
    </section>
  );
}

interface ViewToggleProps {
  table: boolean;
  onToggle: () => void;
  controls: string;
}

/** Every chart has an equivalent table, so values never depend on colour, hover or sight. */
export function ViewToggle({ table, onToggle, controls }: ViewToggleProps) {
  return (
    <button
      type="button"
      onClick={onToggle}
      aria-pressed={table}
      aria-controls={controls}
      className="inline-flex min-h-9 items-center gap-1.5 rounded-lg border border-line bg-surface px-3 text-sm font-medium text-ink-2 hover:bg-surface-2 hover:text-ink"
    >
      <Icon name={table ? 'chart' : 'table'} />
      {table ? 'View as chart' : 'View as table'}
    </button>
  );
}
