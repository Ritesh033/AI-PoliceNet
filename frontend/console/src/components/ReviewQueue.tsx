import { useEffect, useMemo, useState } from 'react';
import type { CaseKind, Incident, Stage } from '../types';
import { CATEGORY_LABEL } from '../data/constants';
import { sortQueue } from '../state/selectors';
import { ago, dueLabel, fmtInt } from '../lib/format';
import { Card } from './Card';
import { Icon } from './Icon';
import { LaneTag, PriorityBadge, STAGE_LABEL } from './Badges';

const PAGE_SIZE = 8;
const STAGES: Stage[] = ['awaiting', 'in_review', 'referred', 'closed'];

interface Props {
  incidents: Incident[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  now: number;
}

function timeCell(i: Incident, stage: Stage, dueText: string, now: number): string {
  if (stage === 'awaiting' || stage === 'in_review') return dueText;
  return ago(stage === 'referred' && i.referredAt ? i.referredAt : i.receivedAt, now);
}

export function ReviewQueue({ incidents, selectedId, onSelect, now }: Props) {
  const [stage, setStage] = useState<Stage>('awaiting');
  const [kind, setKind] = useState<'all' | CaseKind>('all');
  const [page, setPage] = useState(0);

  const stageCounts = useMemo(() => {
    const counts: Record<Stage, number> = { awaiting: 0, in_review: 0, referred: 0, closed: 0 };
    for (const i of incidents) if (kind === 'all' || i.kind === kind) counts[i.stage] += 1;
    return counts;
  }, [incidents, kind]);

  const rows = useMemo(
    () => sortQueue(incidents, stage).filter((i) => kind === 'all' || i.kind === kind),
    [incidents, stage, kind],
  );

  const pages = Math.max(1, Math.ceil(rows.length / PAGE_SIZE));
  const safePage = Math.min(page, pages - 1);
  useEffect(() => {
    if (page !== safePage) setPage(safePage);
  }, [page, safePage]);

  const visible = rows.slice(safePage * PAGE_SIZE, safePage * PAGE_SIZE + PAGE_SIZE);
  const from = rows.length === 0 ? 0 : safePage * PAGE_SIZE + 1;
  const to = Math.min(rows.length, (safePage + 1) * PAGE_SIZE);
  const timeHeading = stage === 'awaiting' || stage === 'in_review' ? 'Review deadline' : stage === 'referred' ? 'Referred' : 'Received';

  return (
    <Card id="queue" title="Incident review queue" subtitle="Sorted by review deadline · social-media alerts and conduct complaints" className="h-full">
      <div className="mb-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div role="group" aria-label="Queue status" className="flex flex-wrap gap-1.5">
          {STAGES.map((s) => (
            <button
              key={s}
              type="button"
              aria-pressed={stage === s}
              onClick={() => {
                setStage(s);
                setPage(0);
              }}
              className={`min-h-9 rounded-lg border px-3 text-sm font-medium ${
                stage === s ? 'border-accent bg-accent text-accent-ink' : 'border-line bg-surface text-ink-2 hover:bg-surface-2 hover:text-ink'
              }`}
            >
              {STAGE_LABEL[s]} <span className="tnum opacity-80">({fmtInt(stageCounts[s])})</span>
            </button>
          ))}
        </div>
        <label className="flex items-center gap-2 text-sm text-ink-2">
          Type
          <select
            value={kind}
            onChange={(e) => {
              setKind(e.target.value as 'all' | CaseKind);
              setPage(0);
            }}
            className="min-h-9 rounded-lg border border-line bg-surface px-2 text-sm text-ink"
          >
            <option value="all">All</option>
            <option value="social">Social media</option>
            <option value="conduct">Accountability</option>
          </select>
        </label>
      </div>

      <div className="overflow-x-auto rounded-lg border border-line">
        <table className="w-full border-collapse text-left text-sm">
          <caption className="sr-only">
            {STAGE_LABEL[stage]} incidents, page {safePage + 1} of {pages}. Select a case ID to open its details.
          </caption>
          <thead className="bg-surface-2 text-ink-2">
            <tr>
              <th scope="col" className="px-3 py-2 font-medium">
                Case
              </th>
              <th scope="col" className="hidden px-3 py-2 font-medium sm:table-cell">
                Priority
              </th>
              <th scope="col" className="hidden px-3 py-2 font-medium md:table-cell">
                Region
              </th>
              <th scope="col" className="hidden px-3 py-2 font-medium sm:table-cell">
                {timeHeading}
              </th>
            </tr>
          </thead>
          <tbody>
            {visible.length === 0 && (
              <tr>
                <td colSpan={4} className="px-3 py-8 text-center text-ink-2">
                  Nothing here yet.
                </td>
              </tr>
            )}
            {visible.map((i) => {
              const selected = i.id === selectedId;
              const due = dueLabel(i.dueAt, now);
              return (
                <tr
                  key={i.id}
                  onClick={() => onSelect(i.id)}
                  className={`cursor-pointer border-t border-line align-top ${selected ? 'bg-accent-soft' : 'hover:bg-surface-2'}`}
                >
                  <td className="max-w-[16rem] px-3 py-2.5">
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelect(i.id);
                      }}
                      aria-current={selected ? 'true' : undefined}
                      className="tnum -ml-1 rounded px-1 font-semibold text-accent-text underline-offset-2 hover:underline"
                    >
                      {i.id}
                    </button>
                    <p className="mt-0.5 text-ink">{i.title}</p>
                    <p className="text-ink-2">{CATEGORY_LABEL[i.category]}</p>
                    <div className="mt-1.5 flex flex-wrap items-center gap-1.5 sm:hidden">
                      <PriorityBadge priority={i.priority} />
                      <LaneTag lane={i.lane} />
                      <span className={`inline-flex items-center gap-1 text-xs ${due.overdue ? 'font-medium text-crit' : 'text-ink-2'}`}>
                        <Icon name="clock" size={12} />
                        {timeCell(i, stage, due.text, now)}
                      </span>
                    </div>
                  </td>
                  <td className="hidden px-3 py-2.5 sm:table-cell">
                    <div className="flex flex-col items-start gap-1">
                      <PriorityBadge priority={i.priority} />
                      <LaneTag lane={i.lane} />
                    </div>
                  </td>
                  <td className="hidden px-3 py-2.5 text-ink-2 md:table-cell">
                    {i.district}
                    <br />
                    <span className="text-ink-3">{i.state}</span>
                  </td>
                  <td className="hidden whitespace-nowrap px-3 py-2.5 text-ink-2 sm:table-cell">
                    {stage === 'awaiting' || stage === 'in_review' ? (
                      <span className={`inline-flex items-center gap-1 ${due.overdue ? 'font-medium text-crit' : ''}`}>
                        <Icon name="clock" size={14} />
                        {due.text}
                      </span>
                    ) : (
                      timeCell(i, stage, due.text, now)
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <nav aria-label="Queue pages" className="mt-3 flex items-center justify-between gap-3 text-sm text-ink-2">
        <p className="tnum" aria-live="polite">
          Showing {fmtInt(from)}–{fmtInt(to)} of {fmtInt(rows.length)}
        </p>
        <div className="flex gap-1.5">
          <button
            type="button"
            onClick={() => setPage(safePage - 1)}
            disabled={safePage === 0}
            aria-label="Previous page"
            className="inline-flex size-9 items-center justify-center rounded-lg border border-line bg-surface hover:bg-surface-2 disabled:opacity-40"
          >
            <Icon name="chevronLeft" />
          </button>
          <button
            type="button"
            onClick={() => setPage(safePage + 1)}
            disabled={safePage >= pages - 1}
            aria-label="Next page"
            className="inline-flex size-9 items-center justify-center rounded-lg border border-line bg-surface hover:bg-surface-2 disabled:opacity-40"
          >
            <Icon name="chevronRight" />
          </button>
        </div>
      </nav>
    </Card>
  );
}
