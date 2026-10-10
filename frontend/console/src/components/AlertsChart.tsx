import { useMemo, useState } from 'react';
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import type { Bucket, CategoryId, Period } from '../types';
import { CATEGORIES, PERIODS } from '../data/constants';
import { fmtCompact, fmtInt } from '../lib/format';
import { Card, ViewToggle } from './Card';

interface Props {
  period: Period;
  buckets: Bucket[];
  perCategory: Record<CategoryId, number>;
  total: number;
  reducedMotion: boolean;
}

interface TooltipRow {
  dataKey?: string | number;
  value?: number | string;
}

interface TooltipProps {
  active?: boolean;
  payload?: readonly TooltipRow[];
  label?: string | number;
}

/** Five equal intervals with round tick values, e.g. 0, 50, 100 ... 250. */
function niceScale(max: number): { top: number; ticks: number[] } {
  const target = Math.max(max, 5);
  const pow = 10 ** Math.floor(Math.log10(target / 5));
  const step = [1, 2, 5, 10].map((m) => m * pow).find((st) => st * 5 >= target) ?? pow * 10;
  return { top: step * 5, ticks: [0, 1, 2, 3, 4, 5].map((i) => i * step) };
}

const UNIT: Record<Period, string> = { '24h': 'hour', '7d': 'day', '30d': 'day' };

function AlertsTooltip({ active, payload, label }: TooltipProps) {
  if (!active || !payload?.length) return null;
  const rows = CATEGORIES.map((c, i) => ({
    ...c,
    color: `var(--s${i + 1})`,
    value: Number(payload.find((p) => p.dataKey === c.id)?.value ?? 0),
  })).reverse();
  const total = rows.reduce((n, r) => n + r.value, 0);
  return (
    <div className="min-w-44 rounded-lg border border-line bg-surface p-3 text-sm shadow-lg">
      <p className="mb-1.5 font-medium text-ink">{label}</p>
      <ul className="space-y-1">
        {rows.map((r) => (
          <li key={r.id} className="flex items-center gap-2">
            <span aria-hidden="true" className="h-0.5 w-3 shrink-0 rounded" style={{ background: r.color, height: 3 }} />
            <span className="tnum font-semibold text-ink">{fmtInt(r.value)}</span>
            <span className="text-ink-2">{r.short}</span>
          </li>
        ))}
      </ul>
      <p className="mt-1.5 border-t border-line pt-1.5 text-ink-2">
        <span className="tnum font-semibold text-ink">{fmtInt(total)}</span> total
      </p>
    </div>
  );
}

export function AlertsChart({ period, buckets, perCategory, total, reducedMotion }: Props) {
  const [table, setTable] = useState(false);
  const periodLabel = PERIODS.find((p) => p.id === period)!.long;
  const unit = UNIT[period];
  const data = useMemo(
    () => buckets.map((b) => ({ label: b.label, ...b.counts })),
    [buckets],
  );
  const scale = useMemo(() => niceScale(Math.max(...buckets.map((b) => b.total))), [buckets]);
  const summary = `Stacked column chart of alerts received per ${unit} over ${periodLabel}, split into ${CATEGORIES.length} categories. ${fmtInt(total)} alerts in total.`;

  return (
    <Card
      id="alerts"
      title="Alerts over time"
      subtitle={`Per ${unit}, by category · ${periodLabel}`}
      actions={<ViewToggle table={table} onToggle={() => setTable((t) => !t)} controls="alerts-view" />}
      className="h-full"
    >
      <ul className="mb-3 flex flex-wrap gap-x-5 gap-y-1.5" aria-label="Categories and totals for the period">
        {CATEGORIES.map((c, i) => (
          <li key={c.id} className="flex items-center gap-2 text-sm">
            <span aria-hidden="true" className="h-3 w-3 shrink-0 rounded-[3px]" style={{ background: `var(--s${i + 1})` }} />
            <span className="text-ink-2">{c.short}</span>
            <span className="tnum font-semibold text-ink">{fmtInt(perCategory[c.id])}</span>
          </li>
        ))}
      </ul>

      <div id="alerts-view" className="min-h-[260px]">
        {table ? (
          <div className="max-h-[280px] overflow-auto rounded-lg border border-line" tabIndex={0} aria-label="Alerts table, scrollable">
            <table className="w-full min-w-[520px] border-collapse text-sm">
              <caption className="sr-only">
                Alerts received per {unit} by category, {periodLabel}
              </caption>
              <thead className="sticky top-0 bg-surface-2 text-left text-ink-2">
                <tr>
                  <th scope="col" className="px-3 py-2 font-medium">
                    {unit === 'hour' ? 'Hour (IST)' : 'Day'}
                  </th>
                  {CATEGORIES.map((c) => (
                    <th key={c.id} scope="col" className="px-3 py-2 text-right font-medium">
                      {c.short}
                    </th>
                  ))}
                  <th scope="col" className="px-3 py-2 text-right font-medium">
                    Total
                  </th>
                </tr>
              </thead>
              <tbody>
                {buckets.map((b) => (
                  <tr key={b.start} className="border-t border-line">
                    <th scope="row" className="px-3 py-1.5 text-left font-medium text-ink">
                      {b.label}
                    </th>
                    {CATEGORIES.map((c) => (
                      <td key={c.id} className="tnum px-3 py-1.5 text-right text-ink-2">
                        {fmtInt(b.counts[c.id])}
                      </td>
                    ))}
                    <td className="tnum px-3 py-1.5 text-right font-semibold text-ink">{fmtInt(b.total)}</td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr className="border-t-2 border-line font-semibold text-ink">
                  <th scope="row" className="px-3 py-2 text-left">
                    Total
                  </th>
                  {CATEGORIES.map((c) => (
                    <td key={c.id} className="tnum px-3 py-2 text-right">
                      {fmtInt(perCategory[c.id])}
                    </td>
                  ))}
                  <td className="tnum px-3 py-2 text-right">{fmtInt(total)}</td>
                </tr>
              </tfoot>
            </table>
          </div>
        ) : (
          <div role="group" aria-label={summary} className="h-[260px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data} margin={{ top: 8, right: 4, left: 0, bottom: 0 }} barCategoryGap="22%">
                <CartesianGrid vertical={false} stroke="var(--line)" />
                <XAxis
                  dataKey="label"
                  tickLine={false}
                  axisLine={{ stroke: 'var(--axis)' }}
                  interval="preserveStartEnd"
                  minTickGap={14}
                  tickMargin={8}
                />
                <YAxis tickLine={false} axisLine={false} width={40} tickFormatter={fmtCompact} domain={[0, scale.top]} ticks={scale.ticks} />
                <Tooltip content={<AlertsTooltip />} isAnimationActive={false} />
                {CATEGORIES.map((c, i) => (
                  <Bar
                    key={c.id}
                    dataKey={c.id}
                    name={c.short}
                    stackId="alerts"
                    fill={`var(--s${i + 1})`}
                    stroke="var(--surface)"
                    strokeWidth={2}
                    maxBarSize={24}
                    radius={i === CATEGORIES.length - 1 ? [4, 4, 0, 0] : 0}
                    isAnimationActive={!reducedMotion}
                  />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    </Card>
  );
}
