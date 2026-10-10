import { Card } from './Card';
import { Icon, type IconName } from './Icon';

const LAYERS: ReadonlyArray<{ icon: IconName; title: string; owner: string; text: string }> = [
  {
    icon: 'radar',
    title: 'AI detection',
    owner: 'Automated, advisory',
    text: 'Flags content or conduct that may need attention and explains why. It never declares anyone guilty.',
  },
  {
    icon: 'fileCheck',
    title: 'Authorized legal action',
    owner: 'Authorized officer',
    text: 'Decides whether the facts and the applicable law justify registration, investigation or referral, following BNSS and IT Act procedure.',
  },
  {
    icon: 'scale',
    title: 'Independent adjudication',
    owner: 'Courts and disciplinary authorities',
    text: 'Determines liability and consequences through due process, with the right to defend and to appeal.',
  },
];

export function DecisionLayers() {
  return (
    <Card id="layers" title="How decisions are made" subtitle="Three separate layers keep accusations from becoming punishments">
      <ol className="grid gap-3 md:grid-cols-3">
        {LAYERS.map((l, idx) => (
          <li key={l.title} className="flex gap-3 rounded-lg bg-surface-2 p-4">
            <span
              aria-hidden="true"
              className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-accent-soft text-accent-text"
            >
              <Icon name={l.icon} size={18} />
            </span>
            <div className="min-w-0">
              <h3 className="text-sm font-semibold text-ink">
                <span className="text-ink-3">{idx + 1}. </span>
                {l.title}
              </h3>
              <p className="text-xs font-medium uppercase tracking-wide text-ink-3">{l.owner}</p>
              <p className="mt-1.5 text-sm leading-6 text-ink-2">{l.text}</p>
            </div>
          </li>
        ))}
      </ol>
    </Card>
  );
}
