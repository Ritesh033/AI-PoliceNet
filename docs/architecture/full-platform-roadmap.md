# Full platform roadmap

The goal is a national system that helps authorized bodies reduce crime and corruption while keeping humans
accountable for every decision. This is the build order. Status is stated plainly.

| # | Layer | Contents | Status |
| --- | --- | --- | --- |
| 1 | Overview console | React + TypeScript dashboard on mock data (`frontend/console`) | Built (demo data) |
| 2 | Case core | Workflow with enforced human decisions, hash-chained ledger, right to respond, appeals (`backend/case-core`) | Built (demo auth) |
| 3 | Identity and deployment (staff only; responders need no login) | OIDC + MFA, role assignment and revocation, PostgreSQL with append-only triggers, external ledger checkpoints, console connected to the API | Next |
| 4 | Evidence vault | Encrypted storage, chain of custody, hashing, access logging, controlled viewer, retention and court-ordered redaction as new ledger entries | Planned |
| 5 | AI detection | Models for threats, harassment, scams, manipulated media and self-confession alerts, plus an evaluation harness with false-positive and bias audits before any pilot; connectors only to authorized feeds | Planned |
| 5b | Lawful identification and notices | Officer-run requests to platforms through legal process, recorded with their legal basis; a public web page for the no-login response link; notice translations | Planned |
| 6 | Accountability | Citizen complaint apps, acknowledgement timers, supervisory routing, findings and appeals, independent oversight views | Planned |
| 7 | Corruption module | See below | Planned |
| 8 | Legal assistant | Retrieval over statutes and precedents; drafts for officers to edit; never files or decides | Planned |
| 9 | Controlled pilot | One jurisdiction, independent performance, privacy and bias audit, sunset and review clauses | Planned |

## Corruption module (layer 7)

Corruption is mostly invisible to video, so it needs different data. All outputs are risk indicators for human
investigators and audit bodies, never accusations.

- **Protected whistleblower intake.** Anonymous channel with identity kept separate from content, and
  protections from retaliation built into the workflow.
- **Public-procurement analytics.** Indicators such as repeated single-bid awards, the same bidders rotating
  wins, clustered prices, and orders split just under approval thresholds. Uses public tender data first.
- **Public-spending anomalies.** Variances against budgets, vendors and benchmarks, routed to audit bodies.
- **Declared-asset consistency.** Only where the law permits and with the competent authority's access.
- **Referral.** To the competent authority (Lokpal or Lokayukta, vigilance commissions, anti-corruption
  bureaus, audit offices) as a human decision, respecting statutory prior-approval requirements.
- **Safeguards.** Every indicator explains itself, carries base rates, is audited for false positives, and
  follows the same right-to-respond workflow as other cases. An anomaly is not evidence of corruption.

## What stays out of scope

See `docs/legal-compliance/design-guardrails.md`: no autonomous arrests, FIR registration or cancellation,
orders, permanent flags, locks on judicial review, emotion-based inference, individual surveillance sweeps or
robots with custody powers.
