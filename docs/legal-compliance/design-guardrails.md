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

## Civic violations and official conduct: a challan or a sanction, not an FIR

Not everything seen on social media is a crime, and the platform does not treat it as one. Every case is on one track
that is fixed when it opens, and the track decides what can follow.

- **Civic violations** (a car parked across a road or highway, spitting gutka, urinating on a public wall, dumping
  waste in a river) are not offences for the purposes of this platform. No FIR can be registered on them. A human
  authorized officer can issue a **challan** to each person an officer has determined to be a subject: the person who
  did it, or the registered owner of the vehicle. Whoever filmed or posted the clip is never one. A challan is not a
  flag and nothing counts it. It can be contested and appealed.
- **Official misconduct that is not an offence in itself** (stopping people and fining them without papers or inquiry,
  keeping private persons alongside to do official work, rude or arbitrary conduct) is considered only when the clip
  shows a person acting in an official capacity, and never when it is a film scene. It goes to the supervisory
  authority, not to the force being filmed. A competent authority can record a **sanction** (warning, fine,
  suspension, licence or contract cancellation, removal order) against **each** person decided to be a subject: the
  official, a private person acting for them, a contractor or licensee. Whoever posted the clip, or was treated that
  way, is never one.
- A sanction needs a **notice** to that person first. A fine, a licence cancellation and a removal order also need the
  person to have been heard (a response on file, or the response window passed; silence is never an admission), and a
  removal order follows an inquiry. A warning or an interim suspension needs the notice but not the full window.
- **Beating or torturing anyone, and demanding a bribe, are offences** for everyone, officials included. They are
  flagged for human review like any other hard behaviour. Whether force was lawful (for example a documented arrest
  on a warrant) is for the human who reviews the facts, not for the model.
- **A count asks; it never acts.** A count of recorded, unrevoked warnings and fines against the same public servant
  asks the supervisory authority for a written review at 3 (whether to suspend, as an interim measure) and at 7
  (whether to open an inquiry for removal). The count is of sanctions that a named human authority recorded after a
  notice, never of raw AI flags and never of challans. It suspends, removes and fines no one, it restricts no court,
  and it falls when a sanction is revoked by the supervisory authority or a court.
- The amounts are set by the law or schedule that applies. The platform's floors (10,000 rupees for a challan,
  1,000,000 for a departmental fine) are **settings that a deployment must replace** with figures a statute or rule
  supports. Existing law does not support every figure: for example, the Police Act, 1861 section 7 caps a fine on a
  subordinate police officer at one month's pay, so a fixed 10 lakh minimum would exceed it. Counsel must confirm.

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
  verified findings by competent authorities, with appeal. The only count the platform keeps, of recorded sanctions
  against a public servant, can ask a human authority for a review and does nothing else.
- Only a human authority issues a challan or records a sanction. A civic or departmental case can never reach an FIR.
- Sensitive media is never previewed in the console; only a hash and metadata are stored in the case record.

## Explicit non-goals (will not be built)

| Idea | Why not |
| --- | --- |
| Automatic arrest or detention from an AI flag | A hacked account, a deepfake or a false complaint would jail an innocent person. Arrest needs a human officer with grounds and accountability. |
| AI deciding FIR cancellation or issuing orders | AI cannot judge intent or context and can be fooled by synthetic video. Adjudication stays with courts. |
| A flag count (for example 3 or 7) that suspends or permanently removes a public servant automatically, beyond the reach of any court or the President | Anyone who can generate flags could remove a rival. Suspension and removal are orders of a competent authority after notice (Article 311(2) requires an inquiry before dismissal, removal or reduction in rank), and judicial review is part of the basic structure of the Constitution. The platform instead asks a human authority for a review at 3 and at 7 recorded sanctions. |
| Software that fines, suspends, cancels a licence or removes anyone | Penalties are orders of a competent authority after notice and a hearing, with a legal basis. The platform records what a named human decides. |
| A fixed minimum fine (for example 10 lakh) imposed by the platform | Amounts come from the law that applies, and a statute can cap them. The floors here are settings for a deployment to replace with figures the law supports. |
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
- Statutory prior-approval requirements before inquiries into public servants (Prevention of Corruption Act, 1988
  section 17A for inquiries into official decisions and section 19 for sanction to prosecute), and which service rules
  govern each class of public servant for suspension, penalties and removal.
- The legal basis and quantum for each civic violation (municipal bylaws, the Motor Vehicles Act, and for waste in a
  river the Water Act as amended in 2024, where discharge now carries a monetary penalty imposed by an adjudicating
  officer after a hearing). Whether a given violation is non-criminal is a legal question, not a platform setting.
- Stable official identifiers: the review count joins sanctions by a pseudonymous reference, so it needs a reference
  that stays the same across cases and that an identity system supplies.
- Retention, redaction and correction rules that coexist with an append-only ledger.
