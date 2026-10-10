# Design guardrails

These are the rules the platform is built to follow. They exist so that an AI error, a hacked account or a
malicious complaint cannot by itself harm an innocent person, and so that every decision has an accountable
human behind it. They are engineering requirements for the code, not legal advice; independent constitutional
and criminal-law experts should review them before any legal adoption.

## Three separate layers

1. **AI detection.** Flags content or conduct that may need attention and explains why. Advisory only.
2. **Authorized legal action.** A human officer decides on registration, investigation or referral under BNSS
   and the IT Act.
3. **Independent adjudication.** Courts and disciplinary authorities decide liability, with appeal rights.

## Must hold (enforced and tested in `backend/case-core`)

- AI never registers, cancels or closes an FIR, issues an order, or arrests anyone.
- Only a human authorized officer registers an FIR, with a written basis. Only a judicial authority closes one.
- The accused cannot "cancel" an FIR by uploading material, and the AI cannot either. A response informs the
  humans who decide, and it is always accepted while the matter is open.
- A response window starts only when a human records that notice was served. When it passes, nothing happens
  automatically to the person. A human is asked to follow up. Silence is never treated as admission.
- Conduct complaints go to an independent supervisory authority, never to the force being complained about, and
  need an inquiry before any FIR decision. Anyone named in a case is barred from acting on it.
- Every decision needs a written reason in a hash-chained ledger that auditors can verify.
- No count of alerts, complaints or flags can restrict anyone's access to any court. Consequences come from
  verified findings by competent authorities, with appeal.
- Sensitive media is never previewed in the console; only a hash and metadata are stored in the case record.

## Explicit non-goals (will not be built)

| Idea | Why not |
| --- | --- |
| Automatic arrest or detention from an AI flag | A hacked account, a deepfake or a false complaint would jail an innocent person. Arrest needs a human officer with grounds and accountability. |
| AI deciding FIR cancellation or issuing orders | AI cannot judge intent or context and can be fooled by synthetic video. Adjudication stays with courts. |
| A flag count (for example 7) that locks an order beyond the Supreme Court | Anyone who can generate flags could permanently remove a rival's legal protection. Judicial review is part of the basic structure of the Constitution. |
| "Permanent suspect" labels | A label from unverified accusations is punishment without a finding and invites abuse. |
| Requiring the accused to upload proof within a deadline or lose the case | Shifts the burden of proof onto the accused and pressures them toward self-incrimination and trial by social media. |
| Emotion, remorse, heart-rate or eye-movement inference as grounds for any legal step | Scientifically unreliable; false positives would fall on frightened or neurodivergent people. |
| City-camera sweeps on individuals to check whether they were "followed" | Surveillance of a person needs a legal basis, necessity and proportionality. Duress is handled by a human wellbeing contact. |
| Robots with arrest or custody powers | Those powers belong to accountable human officers. Robots may do administrative intake. |
| Different processes for leaders and ordinary citizens | Equality before law. |
| Claims that data "cannot be changed or hacked by anyone" | Not achievable. The goal is tamper-evidence with independent checkpoints, and visible court-ordered corrections. |

## Open items for legal review

- Which FIR-registration and preliminary-inquiry rules apply to AI-originated information under BNSS.
- Admissibility of self-uploaded and public-interview confessions and how corroboration is recorded.
- Data protection (DPDP Act 2023) basis for monitoring public content and storing evidence hashes.
- Statutory prior-approval requirements before inquiries into public servants.
- Retention, redaction and correction rules that coexist with an append-only ledger.
