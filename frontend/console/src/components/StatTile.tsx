import { Icon } from './Icon';

interface Delta {
  /** Signed change, already formatted, e.g. "+6.2%". */
  text: string;
  direction: 'up' | 'down' | 'flat';
  versus: string;
}

interface StatTileProps {
  id: string;
  label: string;
  value: string;
  caption: string;
  scope: string;
  delta?: Delta;
  spark?: number[];
}

function Sparkline({ values }: { values: number[] }) {
  const w = 96;
  const h = 32;
  const pad = 5;
  const max = Math.max(...values);
  const min = Math.min(...values);
  const span = max - min || 1;
  const pts = values.map((v, i) => [
    pad + (i / (values.length - 1)) * (w - pad * 2),
    h - pad - ((v - min) / span) * (h - pad * 2),
  ]);
  const last = pts[pts.length - 1];
  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} aria-hidden="true" focusable="false" className="shrink-0">
      <polyline
        points={pts.map((p) => p.join(',')).join(' ')}
        fill="none"
        stroke="var(--axis)"
        strokeWidth={2}
        strokeLinejoin="round"
        strokeLinecap="round"
      />
      <circle cx={last[0]} cy={last[1]} r={4} fill="var(--seq)" stroke="var(--surface)" strokeWidth={2} />
    </svg>
  );
}

export function StatTile({ id, label, value, caption, scope, delta, spark }: StatTileProps) {
  return (
    <section aria-labelledby={`${id}-label`} className="card flex min-w-0 flex-col justify-between gap-3 p-4 sm:p-5">
      <div className="flex items-start justify-between gap-2">
        <h2 id={`${id}-label`} className="text-sm font-medium text-ink-2">
          {label}
        </h2>
        <span className="rounded-full border border-line px-2 py-0.5 text-[11px] font-medium uppercase tracking-wide text-ink-3">
          {scope}
        </span>
      </div>
      <div className="flex items-end justify-between gap-3">
        <p className="text-[2rem] font-semibold leading-none text-ink" aria-live="off">
          {value}
        </p>
        {spark && spark.length > 1 && <Sparkline values={spark} />}
      </div>
      <div className="min-h-10 text-sm leading-5 text-ink-2">
        {delta && (
          <p className="flex flex-wrap items-center gap-x-1.5">
            <span className="inline-flex items-center gap-0.5 font-medium text-ink">
              <Icon name={delta.direction === 'up' ? 'arrowUp' : delta.direction === 'down' ? 'arrowDown' : 'minus'} size={14} />
              {delta.text}
            </span>
            <span>{delta.versus}</span>
          </p>
        )}
        <p>{caption}</p>
      </div>
    </section>
  );
}
