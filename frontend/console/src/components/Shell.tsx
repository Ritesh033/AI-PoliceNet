import { useRef, type KeyboardEvent } from 'react';
import type { Theme } from '../hooks';
import { Icon } from './Icon';

export function DemoBanner() {
  return (
    <section aria-label="Demo notice" className="border-b border-warn/50 bg-warn-soft px-4 py-2 text-sm text-ink">
      <p className="mx-auto flex max-w-[1400px] items-start gap-2">
        <Icon name="info" size={18} className="mt-0.5 shrink-0 text-warn-ink" />
        <span>
          <strong className="font-semibold">DEMO ONLY.</strong> Illustrative interface. All figures are sample data, not live Indian police
          records. This console is not connected to any social-media account or police system.
        </span>
      </p>
    </section>
  );
}

export function Header({ theme, onToggleTheme }: { theme: Theme; onToggleTheme: () => void }) {
  return (
    <header className="sticky top-0 z-20 border-b border-line bg-surface/95 backdrop-blur">
      <div className="mx-auto flex max-w-[1400px] items-center justify-between gap-3 px-4 py-3 sm:px-6">
        <div className="flex min-w-0 items-center gap-3">
          <span aria-hidden="true" className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-accent text-accent-ink">
            <Icon name="shield" size={22} />
          </span>
          <div className="min-w-0">
            <p className="truncate text-base font-semibold tracking-wide text-ink">AI POLICING NET</p>
            <p className="truncate text-xs tracking-wide text-ink-2">PUBLIC SAFETY &amp; ACCOUNTABILITY CONSOLE</p>
          </div>
          <span className="ml-1 shrink-0 rounded-full border border-warn/60 bg-warn-soft px-2.5 py-0.5 text-xs font-bold tracking-widest text-warn-ink">
            DEMO
          </span>
        </div>
        <button
          type="button"
          onClick={onToggleTheme}
          aria-label={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
          className="inline-flex size-10 shrink-0 items-center justify-center rounded-lg border border-line bg-surface text-ink-2 hover:bg-surface-2 hover:text-ink"
        >
          <Icon name={theme === 'dark' ? 'sun' : 'moon'} size={18} />
        </button>
      </div>
    </header>
  );
}

export interface TabDef {
  id: string;
  label: string;
}

interface TabsProps {
  tabs: readonly TabDef[];
  active: string;
  onChange: (id: string) => void;
}

/** WAI-ARIA tabs with automatic activation and roving tabindex. */
export function Tabs({ tabs, active, onChange }: TabsProps) {
  const refs = useRef<Record<string, HTMLButtonElement | null>>({});

  const onKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    const index = tabs.findIndex((t) => t.id === active);
    let next = index;
    if (e.key === 'ArrowRight') next = (index + 1) % tabs.length;
    else if (e.key === 'ArrowLeft') next = (index - 1 + tabs.length) % tabs.length;
    else if (e.key === 'Home') next = 0;
    else if (e.key === 'End') next = tabs.length - 1;
    else return;
    e.preventDefault();
    onChange(tabs[next].id);
    refs.current[tabs[next].id]?.focus();
  };

  return (
    <div role="tablist" aria-label="Console sections" onKeyDown={onKeyDown} className="-mb-px flex gap-1 overflow-x-auto">
      {tabs.map((t) => {
        const selected = t.id === active;
        return (
          <button
            key={t.id}
            ref={(el) => {
              refs.current[t.id] = el;
            }}
            role="tab"
            type="button"
            id={`tab-${t.id}`}
            aria-selected={selected}
            aria-controls={`panel-${t.id}`}
            tabIndex={selected ? 0 : -1}
            onClick={() => onChange(t.id)}
            className={`min-h-11 whitespace-nowrap border-b-2 px-4 text-sm font-medium ${
              selected ? 'border-accent text-ink' : 'border-transparent text-ink-2 hover:border-axis hover:text-ink'
            }`}
          >
            {t.label}
          </button>
        );
      })}
    </div>
  );
}

interface PlaceholderProps {
  id: string;
  title: string;
  module: string;
  items: readonly string[];
}

export function Placeholder({ id, title, module, items }: PlaceholderProps) {
  return (
    <div role="tabpanel" id={`panel-${id}`} aria-labelledby={`tab-${id}`} tabIndex={0} className="card p-5 sm:p-6">
      <p className="text-xs font-medium uppercase tracking-wide text-ink-3">{module} · planned</p>
      <h2 className="mt-1 text-lg font-semibold text-ink">{title}</h2>
      <p className="mt-2 max-w-2xl text-sm leading-6 text-ink-2">
        This prototype build covers the Overview only. This section is outlined here so the navigation reflects the roadmap.
      </p>
      <ul className="mt-3 max-w-2xl list-disc space-y-1.5 pl-5 text-sm leading-6 text-ink-2 marker:text-ink-3">
        {items.map((i) => (
          <li key={i}>{i}</li>
        ))}
      </ul>
    </div>
  );
}
