import { useState } from 'react';
import { Bar, BarChart, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { fmtInt } from '../lib/format';
import { Card, ViewToggle } from './Card';

interface Props {
  rows: Array<{ state: string; value: number }>;
  reducedMotion: boolean;
}

interface TooltipProps {
  active?: boolean;
  payload?: ReadonlyArray<{ payload?: { state: string; value: number } }>;
}

function StateTooltip({ active, payload }: TooltipProps) {
  const row = payload?.[0]?.payload;
  if (!active || !row) return null;
  return (
    <div className="rounded-lg border border-line bg-surface p-2.5 text-sm shadow-lg">
      <p className="tnum font-semibold text-ink">{fmtInt(row.value)}</p>
      <p className="text-ink-2">{row.state}, awaiting review</p>
    </div>
  );
}

export function StateChart({ rows, reducedMotion }: Props) {
  const [table, setTable] = useState(false);
  const total = rows.reduce((n, r) => n + r.value, 0);
  const summary = `Bar chart of ${fmtInt(total)} items awaiting review across ${rows.length} states. Highest: ${rows[0]?.state} with ${rows[0]?.value}.`;
  return (
    <Card
      id="states"
      title="Awaiting review by state"
      subtitle="Current queue · sample jurisdictions"
      actions={<ViewToggle table={table} onToggle={() => setTable((t) => !t)} controls="states-view" />}
      className="h-full"
    >
      <div id="states-view">
        {table ? (
          <table className="w-full border-collapse text-sm">
            <caption className="sr-only">Items awaiting review by state</caption>
            <thead className="text-left text-ink-2">
              <tr>
                <th scope="col" className="border-b border-line py-2 font-medium">
                  State
                </th>
                <th scope="col" className="border-b border-line py-2 text-right font-medium">
                  Awaiting review
                </th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.state}>
                  <th scope="row" className="border-b border-line py-1.5 text-left font-medium text-ink">
                    {r.state}
                  </th>
                  <td className="tnum border-b border-line py-1.5 text-right text-ink-2">{fmtInt(r.value)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div role="group" aria-label={summary} className="h-[292px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={rows} layout="vertical" margin={{ top: 0, right: 28, left: 0, bottom: 0 }} barCategoryGap="30%">
                <XAxis type="number" hide domain={[0, 'dataMax']} />
                <YAxis
                  type="category"
                  dataKey="state"
                  width={104}
                  tickLine={false}
                  axisLine={{ stroke: 'var(--axis)' }}
                  tickMargin={6}
                  interval={0}
                />
                <Tooltip content={<StateTooltip />} isAnimationActive={false} />
                <Bar dataKey="value" fill="var(--seq)" maxBarSize={20} radius={[0, 4, 4, 0]} isAnimationActive={!reducedMotion}>
                  <LabelList dataKey="value" position="right" fill="var(--ink-2)" fontSize={12} />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    </Card>
  );
}
