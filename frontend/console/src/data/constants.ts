import type { CategoryId, IncidentCategory, Period, Priority, ReviewLane, Triage } from '../types';
import { TIME } from '../lib/format';

export const CATEGORIES: ReadonlyArray<{ id: CategoryId; label: string; short: string; share: number }> = [
  { id: 'threat', label: 'Threats & harassment', short: 'Threats', share: 0.34 },
  { id: 'scam', label: 'Scams & impersonation', short: 'Scams', share: 0.26 },
  { id: 'ncii', label: 'Suspected sexual / non-consensual content', short: 'Sexual / NCII', share: 0.17 },
  { id: 'hate', label: 'Incitement & hate', short: 'Incitement', share: 0.14 },
  { id: 'manipulated', label: 'Manipulated media', short: 'Manipulated', share: 0.09 },
];

export const CATEGORY_LABEL: Record<IncidentCategory, string> = {
  threat: 'Threats & harassment',
  scam: 'Scams & impersonation',
  ncii: 'Suspected sexual / non-consensual content',
  hate: 'Incitement & hate',
  manipulated: 'Manipulated media',
  conduct: 'Official conduct complaint',
};

export const PERIODS: ReadonlyArray<{ id: Period; label: string; long: string; ms: number }> = [
  { id: '24h', label: '24 hours', long: 'the last 24 hours', ms: TIME.DAY },
  { id: '7d', label: '7 days', long: 'the last 7 days', ms: 7 * TIME.DAY },
  { id: '30d', label: '30 days', long: 'the last 30 days', ms: 30 * TIME.DAY },
];

export const TRIAGE: ReadonlyArray<{ id: Triage; label: string; hint: string; weight: number }> = [
  { id: 'urgent', label: 'Urgent threat', hint: 'Immediate human review', weight: 62 },
  { id: 'review', label: 'Needs review', hint: 'Queued for a reviewer', weight: 411 },
  { id: 'none', label: 'No action', hint: 'Closed after triage', weight: 811 },
];

/** Review deadlines by priority. */
export const SLA_MS: Record<Priority, number> = {
  urgent: TIME.HOUR,
  high: 24 * TIME.HOUR,
  routine: 72 * TIME.HOUR,
};

export const PRIORITY_RANK: Record<Priority, number> = { urgent: 0, high: 1, routine: 2 };

export const REGIONS: ReadonlyArray<{ state: string; districts: readonly string[]; weight: number }> = [
  { state: 'Maharashtra', districts: ['Pune', 'Thane', 'Nagpur'], weight: 18 },
  { state: 'Uttar Pradesh', districts: ['Lucknow', 'Kanpur', 'Varanasi'], weight: 16 },
  { state: 'Delhi', districts: ['New Delhi', 'South Delhi'], weight: 12 },
  { state: 'Karnataka', districts: ['Bengaluru Urban', 'Mysuru'], weight: 11 },
  { state: 'Tamil Nadu', districts: ['Chennai', 'Coimbatore'], weight: 9 },
  { state: 'West Bengal', districts: ['Kolkata', 'Howrah'], weight: 8 },
  { state: 'Gujarat', districts: ['Ahmedabad', 'Surat'], weight: 7 },
  { state: 'Rajasthan', districts: ['Jaipur', 'Jodhpur'], weight: 6 },
];

export const PLATFORMS = [
  'Short-video platform',
  'Video-sharing platform',
  'Microblogging platform',
  'Photo-sharing platform',
  'Public messaging channel',
] as const;

export interface IncidentTemplate {
  category: IncidentCategory;
  title: string;
  summary: string;
  signals: string[];
  nextStep: string;
  lane: ReviewLane;
  sources: string[];
  sensitive?: boolean;
}

const FEED = 'Authorized platform feed';
const CITIZEN = 'Citizen report';
const URL_REPORT = 'Public URL report';

export const SOCIAL_TEMPLATES: readonly IncidentTemplate[] = [
  {
    category: 'threat',
    title: 'Reported threat of violence in a public video',
    summary:
      'Spoken statements in a public video appear to threaten violence against an identifiable individual.',
    signals: [
      'Speech-to-text flagged an explicit reference to physical harm',
      'Target appears identifiable from the caption or tags',
      'Corroborated by independent citizen reports',
      'Sarcasm / fiction classifier: inconclusive',
    ],
    nextStep:
      'Verify context and whether the target is identifiable, then refer to the cybercrime desk for authorized review.',
    lane: 'Priority review',
    sources: [CITIZEN, FEED],
  },
  {
    category: 'threat',
    title: 'Targeted harassment campaign in comments',
    summary: 'A cluster of comments directs repeated abusive messages at one account holder.',
    signals: [
      'Burst of 40+ comments from related accounts within 30 minutes',
      'Language classifier: targeted abuse rather than general criticism',
      'Reporter is the targeted account holder',
    ],
    nextStep: 'Confirm the pattern with the reporter, preserve the thread, and assess whether a complaint is warranted.',
    lane: 'Standard review',
    sources: [CITIZEN, URL_REPORT],
  },
  {
    category: 'threat',
    title: 'Blackmail attempt reported with message screenshots',
    summary:
      'A citizen submitted screenshots of messages demanding payment under threat of publishing private images.',
    signals: [
      'Message text matches extortion patterns',
      'Payment handle referenced (not verified)',
      'Screenshots are reporter-provided; authenticity unverified',
    ],
    nextStep: 'Preserve the screenshots with hashes, offer victim-support contact, and route to the cybercrime desk.',
    lane: 'Evidence review',
    sources: [CITIZEN],
  },
  {
    category: 'ncii',
    title: 'Suspected non-consensual intimate content',
    summary:
      'The classifier flagged a public post as possibly containing intimate imagery shared without apparent consent. Preview withheld.',
    signals: [
      'Visual classifier: possible intimate content (flag only)',
      'Caption suggests the person depicted did not consent',
      'No match in the sample known-content registry',
    ],
    nextStep:
      'Preserve evidence, follow the victim-support protocol, and ask an authorized officer to consider a takedown request through the proper channel.',
    lane: 'Evidence review',
    sources: [CITIZEN, FEED],
    sensitive: true,
  },
  {
    category: 'ncii',
    title: 'Sexually explicit video posted publicly',
    summary:
      'A public post contains sexually explicit material and the posting account appears to be the original uploader. Preview withheld.',
    signals: [
      'Visual classifier: explicit content (flag only)',
      'Account appears to be the original uploader',
      'Consent and coercion status: unknown',
    ],
    nextStep:
      'Preserve evidence and establish whether anyone depicted is a victim before any action; escalate to an authorized officer to assess applicable provisions.',
    lane: 'Legal review',
    sources: [FEED, URL_REPORT],
    sensitive: true,
  },
  {
    category: 'scam',
    title: 'Impersonation of an official account',
    summary: 'A profile uses an official’s name and photograph to solicit payments from followers.',
    signals: [
      'Profile image matches a verified account',
      'Account created 3 days ago',
      'Payment links in the profile bio',
    ],
    nextStep: 'Confirm with the impersonated office and request platform action through an authorized channel.',
    lane: 'Standard review',
    sources: [FEED, CITIZEN],
  },
  {
    category: 'scam',
    title: 'Donation appeal built on a miracle-cure claim',
    summary:
      'A promotional video claims to cure a serious illness through a ritual and asks viewers to donate.',
    signals: [
      'Claim of curing a serious illness with no verifiable evidence',
      'Donation link in the description',
      'Multiple viewer complaints',
    ],
    nextStep:
      'Assess whether a specific offence (for example fraud) may apply. A miracle claim alone is not an offence.',
    lane: 'Legal review',
    sources: [CITIZEN, URL_REPORT],
  },
  {
    category: 'hate',
    title: 'Posts that may call for violence against a community',
    summary:
      'A set of posts uses language that may incite violence against a community. Criticism or satire alone is not flagged.',
    signals: [
      'Language classifier: call to action involving violence',
      'Targets a group rather than an idea or institution',
      'Rapid resharing across public accounts',
    ],
    nextStep: 'Reviewer to assess context and intent before any referral; protected expression must not be actioned.',
    lane: 'Legal review',
    sources: [FEED],
  },
  {
    category: 'hate',
    title: 'Coordinated false claim that may provoke tension',
    summary: 'Several accounts are spreading an unverified claim that could provoke communal tension.',
    signals: [
      'Identical text posted by 18 accounts in 20 minutes',
      'Claim contradicted by a fact-check source (sample)',
      'No call for violence detected',
    ],
    nextStep: 'Reviewer to verify the claim and decide whether a fact-check notice or referral is appropriate.',
    lane: 'Standard review',
    sources: [FEED, URL_REPORT],
  },
  {
    category: 'manipulated',
    title: 'Likely manipulated video of a public figure',
    summary: 'A viral clip shows signs of face and voice manipulation and carries no provenance information.',
    signals: ['Face-swap artefacts detected', 'Audio and lip movement out of sync', 'No provenance metadata'],
    nextStep: 'Run a second-model check and seek confirmation from the person depicted before any action.',
    lane: 'Evidence review',
    sources: [FEED, CITIZEN],
  },
  {
    category: 'manipulated',
    title: 'Synthetic celebrity endorsement for an investment scheme',
    summary: 'An advertisement uses what appears to be a synthetic voice to endorse a high-return scheme.',
    signals: ['Synthetic-voice classifier: likely', 'Landing page requests UPI deposits', 'Ad runs from a new account'],
    nextStep: 'Preserve the ad and landing page, then refer to the financial-fraud desk after reviewer verification.',
    lane: 'Standard review',
    sources: [CITIZEN, URL_REPORT],
  },
];

export interface ConductTemplate {
  title: string;
  summary: string;
  signals: string[];
  nextStep: string;
  sources: string[];
}

export const CONDUCT_TEMPLATES: readonly ConductTemplate[] = [
  {
    title: 'Citizen conduct complaint: abusive language',
    summary:
      'A citizen submitted a recording and written complaint alleging abusive language by a government employee during routine document verification. No arrest, FIR or warrant is linked to the complainant.',
    signals: [
      'Transcript: 4 segments flagged as abusive or demeaning',
      'Recording provenance: submitted by the complainant; lawful-recording check pending',
      'No custody or investigation linked to the complainant',
      'Matches the sample “courteous conduct toward the public” rule',
    ],
    nextStep:
      'Route to the independent supervisory authority and acknowledge to the complainant within 24 hours. No disciplinary inference is drawn from this flag alone.',
    sources: ['Citizen complaint (web)', 'Citizen complaint (mobile)'],
  },
  {
    title: 'Complaint of discriminatory remarks at a service counter',
    summary: 'A complainant reports discriminatory remarks while applying for a certificate. No recording was provided.',
    signals: [
      'Statement only; no recording attached',
      'Two other complaints about the same counter in 60 days (unverified)',
      'Matches the sample non-discrimination rule',
    ],
    nextStep: 'Request a statement from the office head and invite the complainant to share any supporting material.',
    sources: ['Citizen complaint (web)'],
  },
  {
    title: 'Complaint of delay or refusal to accept an application',
    summary: 'The complainant says an application was refused without a reason and not recorded for nine days.',
    signals: [
      'Procedural timeline: 9 days since submission',
      'No written refusal on file',
      'Matches the sample “timely service” rule',
    ],
    nextStep: 'Ask the department for the application record and issue a time-bound clarification request.',
    sources: ['Citizen complaint (web)', 'Citizen complaint (mobile)'],
  },
  {
    title: 'Complaint of raised voice and threats during a routine check',
    summary: 'A resident alleges threatening language during a routine vehicle check. Body-camera footage may exist.',
    signals: [
      'Audio clip supplied by the complainant',
      'Speech analysis: raised voice, one threatening phrase (low confidence)',
      'Body-camera footage requested (not yet received)',
    ],
    nextStep: 'Request the body-camera footage and route to the supervisory authority for context-based review.',
    sources: ['Citizen complaint (mobile)'],
  },
];

/** Static stage counts for open conduct complaints (the supervisor-review stage is derived from live data). */
export const COMPLAINT_BASE = {
  acknowledged: 30,
  investigation: 46,
  finding: 29,
  appeal: 18,
} as const;

export const COMPLAINT_METRICS = {
  overdue: 9,
  acknowledgedWithin24h: 0.91,
  acknowledgementTarget: 0.95,
} as const;
