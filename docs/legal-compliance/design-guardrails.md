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

## Flagging policy: context decides, not keywords

A flag is only a consequence-free request for a human to look at one clip. It attaches to the clip, never to a
person. The default policy is a configurable list that legal experts own:

- **Not flagged:** casual or friendly profanity, general-talk abuse, insults, criticism and false statements on
  their own. The model must judge intent and situation, not match words: common Hindi profanity carries sexual
  references literally and would otherwise flag millions of ordinary conversations.
- **Flagged only with aggravating context:** aggressive abuse, when the situation shows repeated targeting of a
  private person, a coordinated campaign against a private person, a power imbalance, or a minor as the target.
- **Never flagged on that basis alone:** crude abuse of or criticism aimed at the Prime Minister, ministers or any
  public official. Officials get no extra protection from criticism, so the platform cannot be used to suppress
  it. Threats against anyone, officials included, are flagged like any other threat.
- **Always flagged for human review:** threats, extortion, fraud, impersonation, sexually explicit material,
  sexual harassment, non-consensual imagery, content involving a child, incitement to violence, and abuse
  targeting a person or group for caste, religion or another protected trait.

Before any referral the AI must also check whether the clip is from a film, show or skit, whether it is edited or
partial, what the full original shows, and where else the clip appears. Only copies of the specific clip are
gathered from public or authorized sources; requests to a platform for user data are made by an authorized officer
through legal process.

## Who is the suspect: the person who did it, not whoever appears in or hosts the video

Each flagged case can carry a scenario, and the scenario fixes which party roles can ever be a subject. Parties are
pseudonymous references from the platform feed. The AI proposes roles; only an authorized officer decides.

- **Intimate imagery shared without consent** (for example a private video of two adults posted by someone else): the
  people shown are victims and are never subjects. The uploader, a sharer or the person who secretly recorded it can be.
- **A public indecent act** (for example nudity at a live show or in a public place): the person performing it is the
  subject. The person who filmed it or posted it is not, unless they did something else wrong, such as extortion or
  harassment, which is flagged on its own behaviour.
- **Explicit content published by those who made or share it:** the person who published it can be a subject. Someone
  who also appears in it is judged separately in each role.
- An FIR in these cases cannot be registered until an officer has decided who is a subject, a victim or a witness.

## Notices and identification

- The platform never looks up, stores or messages anyone's name, phone number, email or WhatsApp number. The schema has
  no place for them, and the service imports no outbound-network library (both are tests).
- Identifying a person behind an account is a legal-process step by an authorized officer (for example a lawful request
  to the platform), recorded in the ledger with its legal basis. It is refused for victims, witnesses and uninvolved
  people.
- A notice goes only to a party an officer has determined to be a subject, never to a victim. It is plain language and
  says why the clip was flagged, what was checked, that an officer and not a machine decided, that an FIR is not a
  finding of guilt, how to respond, that nothing happens automatically if time passes, and that the system never asks
  for money, OTPs or documents. An officer delivers it through a lawful channel and records that they did.
- Responding needs no login. A private link in the notice is the only credential: anyone holding it can upload the full
  original video or any other material from any account or device without saying who they are. The AI matches uploads
  to the flagged clip and can recommend dismissal; a human reads every response and only a court can close an FIR.
- Staff do need to be identified, because every decision must be attributable to an accountable person. A system with no
  staff identity could not tell who registered an FIR.
- Government employees get exactly the same notice, response and review rights as anyone else.

## Must hold (enforced and tested in `backend/case-core`)

- AI never registers, cancels or closes an FIR, issues an order, or arrests anyone.
- Only a human authorized officer registers an FIR, with a written basis. Only a judicial authority closes one.
- A 24-hour clock asks a human to decide on a flagged clip. A missed deadline escalates to a supervisor and never
  files anything.
- One FIR per clip. A repeat alert or a related clip adds information to the existing case instead of opening a
  second FIR, and a court can permit a fresh registration (for example when the full original surfaces later).
- For the response period the AI keeps researching and can recommend dismissal to the court. It never cancels an
  FIR itself.
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
| A system installed across all platforms that collects everything about suspects | Platforms do not allow it, and mass collection is surveillance. Data comes through authorized channels and public sources, and requests for user data go through legal process by an officer. |
| AI automatically finding a person's WhatsApp number, phone or email and messaging them | Automated identification and contact-harvesting of private people, with no legal process. A wrong match would accuse an innocent person, and an automated message can look like a scam. |
| Treating the person shown in a private video, or the person who filmed or posted a public act, as the suspect by default | The suspect is the person who committed the offence. See the scenario rules above. |
| Claims that data "cannot be changed or hacked by anyone" | Not achievable. The goal is tamper-evidence with independent checkpoints, and visible court-ordered corrections. |

## Open items for legal review

- The exact list of hard behaviours and aggravators, mapped to specific offences, including which are cognizable,
  which need the aggrieved person's complaint, and which need a magistrate's order before investigation.
- Whether a second FIR on the same clip is barred in all circumstances, and when fresh information must go to the
  existing investigation.
- Which FIR-registration and preliminary-inquiry rules apply to AI-originated information under BNSS.
- Admissibility of self-uploaded and public-interview confessions and how corroboration is recorded.
- Data protection (DPDP Act 2023) basis for monitoring public content and storing evidence hashes.
- Statutory prior-approval requirements before inquiries into public servants.
- Retention, redaction and correction rules that coexist with an append-only ledger.
