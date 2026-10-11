# AI Policing Net: Overview Console (DEMO)

A working React + TypeScript front end for the **Overview** view of the AI Policing Net
public-safety and accountability console.

> **Demo only.** Every figure is generated sample data. The app makes **no network requests**
> and is not connected to any social-media account, platform API or police system. Nothing here
> files an FIR, suspends an officer or removes content.

## Run it

```bash
cd frontend/console
npm install
npm run dev          # http://localhost:3100
npm test             # vitest: data invariants + component behaviour
npm run build        # typecheck + production build into dist/
```

Requires Node 22+ (the test environment's `jsdom` dependency needs it).

## What is on the Overview

| Area | What it shows |
| --- | --- |
| Header and banner | Product name, a persistent **DEMO ONLY** notice, a `DEMO` pill, light/dark toggle |
| Stat tiles | Alerts received (1,284), awaiting review (76), urgent referrals (12), open complaints (143) |
| Alerts over time | Stacked columns by category for 24 hours / 7 days / 30 days, with a table view |
| Triage outcomes | Urgent threat, needs review, no action |
| Incident review queue | Queue sorted by review deadline (APN-1001 to APN-1003 first, as in the prototype) with status and type filters |
| Case details | Why the item was flagged, model confidence, evidence hash, suggested next step, audit trail, human-review actions |
| Awaiting review by state | Current queue by sample jurisdiction, with a table view |
| Open conduct complaints | Stage breakdown, overdue count, acknowledgement-within-24h meter |
| Live activity | Simulated events generated in the browser; can be paused |
| How decisions are made | The three separate layers: AI detection, authorized legal action, independent adjudication |

The **Social media**, **Accountability** and **Legal cases** tabs are placeholders that outline the
planned modules.

## Case core (live) tab

The one tab that talks to a real service: the [`backend/case-core`](../../backend/case-core) API, which you run
yourself. Everything stays local and uses invented sample data; sign-in is the API's demo header stub.

```bash
# terminal 1: the API, seeded with sample cases (CORS allows the console origin)
cd backend/case-core && python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
export APN_ENV=demo APN_CORS_ORIGINS=http://localhost:3100 APN_CHECKPOINT_KEY=change-me
python -m app.demo_seed && uvicorn app.main:app --port 8100
# terminal 2: this console
cd frontend/console && npm run dev      # then open the "Case core (live)" tab and click Connect
```

What it shows, all enforced by the server and not by this page:

- Cases with the human-decision deadline, the model's detected behaviours, and the full-context checklist (film or
  show match, edits, full original, other copies) that must be complete before any referral.
- Evidence as hashes only, with "preview withheld" for sensitive items.
- Human decisions with a written reason. Switch **Act as** to a role that should not take a step and the server's
  refusal appears verbatim (for example a reviewer trying to close an FIR, or the AI trying to register one).
- AI advice marked non-binding, including a dismissal recommendation that only a court can act on.
- **Who is who:** parties proposed by the AI and decided by an officer. The server refuses to name a victim a subject (or,
  in a public indecent act, the person who filmed or posted it), and refuses to send a notice to anyone but a decided subject.
- **Notice package:** after an officer records a notice, the full notice text and the private no-login response link are
  shown once. The platform never sends messages or looks anyone up.
- The hash-chained ledger and a **Verify ledger integrity** button, for auditors and judicial authorities.

## Design decisions that follow the product rules

- **AI is advisory.** Review actions (assign, request context, no action, refer) are always a human
  step. Nothing is registered or punished automatically, and the UI says so where actions are taken.
- **Complaint counts do not decide outcomes.** The complaints panel says findings follow verified
  evidence, service rules and appeal rights.
- **Conduct complaints are routed to a supervisory authority**, not to an arresting or investigating
  officer, and carry no disciplinary inference from an AI flag alone.
- **Sensitive media is never displayed.** Items flagged as suspected sexual or non-consensual content
  show "Preview withheld"; only a hash and a sample locator are shown.
- **No real identities.** Platforms are generic ("Short-video platform"), locators are
  `evidence://sample/...`, and there are no real accounts, URLs or named officers.
- **Reconciled numbers.** The seed data is built so the headline figures match the prototype exactly
  and every other number is derived from the same records (see `src/data/seed.ts`).
- **Period vs current.** The period selector scopes alerts, triage and referrals; queue, complaints
  and state figures always show current status, and each tile is tagged *Period* or *Current*.

## Accessibility

- Skip link, landmarks, one `h1`, and a WAI-ARIA tab pattern with arrow/Home/End keys.
- Every chart has an equivalent **table view**, and tooltips are not required to read any value.
- Status is never colour alone: priorities and triage outcomes carry an icon and a text label.
- Visible focus rings, 36-44 px controls, reduced-motion support, and light/dark themes.
- The live feed has a **Pause** control and is not announced to screen readers (`aria-live="off"`).
- Chart series colours are the validated categorical palette (adjacent-pair colour-blind separation
  passes in both themes). The light-theme contrast notes for three series are covered by the legend
  totals and table view.
- Checked with axe-core (WCAG 2.2 A/AA + best practice): no violations in desktop light, desktop dark
  and mobile.

## Structure

```
src/
  App.tsx                 page composition, live simulation wiring
  components/             cards, charts, queue, case details, shell, tabs
  data/constants.ts       categories, regions, incident templates, SLAs
  data/seed.ts            deterministic mock-data generator (seeded PRNG)
  state/consoleState.ts   reducer: review actions, live ticks, reset
  state/selectors.ts      derived numbers (period stats, queue, complaints)
  state/liveTick.ts       pure generator for one simulated incoming alert
  lib/                    formatting (en-IN, IST) and random helpers
```

## Next steps (not in this build)

- FastAPI backend with PostgreSQL, authentication and role-based views.
- Replace the seed with API data and WebSockets; keep the same types in `src/types.ts`.
- Map view (MapLibre) once real district-level data exists.
- Wire the placeholder tabs to their modules.
