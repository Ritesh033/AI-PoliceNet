export type ApiRole = 'reviewer' | 'authorized_officer' | 'supervisory_authority' | 'judicial_authority' | 'auditor';

/** Staff roles the demo console can act as. Identity here is the demo header stub of the case-core API. */
export const API_ROLES: ReadonlyArray<{ id: ApiRole; label: string; actorId: string; blurb: string }> = [
  { id: 'reviewer', label: 'Reviewer', actorId: 'rev-demo', blurb: 'Triage and refer; cannot register an FIR' },
  { id: 'authorized_officer', label: 'Authorized officer', actorId: 'off-demo', blurb: 'Registers FIRs and serves notice' },
  { id: 'supervisory_authority', label: 'Supervisory authority', actorId: 'sup-demo', blurb: 'Handles conduct complaints' },
  { id: 'judicial_authority', label: 'Judicial authority', actorId: 'judge-demo', blurb: 'Closes FIRs; reads the ledger' },
  { id: 'auditor', label: 'Auditor', actorId: 'aud-demo', blurb: 'Reads and verifies the ledger' },
];

export type ApiStage =
  | 'received'
  | 'in_review'
  | 'referred'
  | 'inquiry'
  | 'fir_registered'
  | 'closed_no_action'
  | 'closed_by_court'
  | 'linked'
  | 'penalty_recorded';

/** What kind of consequence a case can lead to. Only a criminal case can lead to an FIR. */
export type ApiTrack = 'criminal' | 'civic' | 'departmental';

export interface ApiPenalty {
  id: number;
  party_ref: string;
  party_role: string;
  kind: 'challan' | 'warning' | 'fine' | 'suspension' | 'licence_cancellation' | 'removal_order';
  amount_inr: number | null;
  legal_basis: string;
  issued_by: string;
  issued_at: string;
  revoked: boolean;
  revoked_by: string | null;
  revoked_note: string | null;
}

export interface ApiReview {
  party_ref: string;
  threshold: number;
  count: number;
  kind: string;
}

export interface ApiItem {
  id: number;
  kind: 'evidence' | 'response' | 'advisory' | 'context_finding' | 'notice';
  label: string;
  outcome: 'supports_flag' | 'undermines_flag' | 'inconclusive' | null;
  description: string;
  sha256: string | null;
  preview_withheld: boolean;
  late: boolean;
  added_by: string;
  added_at: string;
}

export interface ApiParty {
  ref: string;
  role: string;
  rationale: string;
  proposed_by: string;
  determination: 'subject' | 'victim' | 'witness' | 'not_involved' | null;
  determined_note: string | null;
}

export interface ApiCase {
  id: string;
  kind: 'social' | 'conduct';
  category: string;
  title: string;
  summary: string;
  priority: 'urgent' | 'high' | 'routine';
  confidence: number;
  stage: ApiStage;
  track: ApiTrack;
  signals?: string[];
  behaviors: string[];
  situation: string[];
  scenario: string;
  parties?: ApiParty[];
  content_fingerprint: string | null;
  checks: string[];
  referred_to_role: string | null;
  notice_served_at: string | null;
  window_closes_at: string | null;
  response_received: boolean;
  court_reviewed: boolean;
  appeal_open: boolean;
  decision_due_at: string | null;
  sla_breached: boolean;
  linked_to: string | null;
  dismissal_recommended: boolean;
  fresh_registration_permitted: boolean;
  context_missing: string[];
  context_findings_undermining_flag: number;
  created_at: string;
  updated_at: string;
  items: ApiItem[];
  /** Staff only: challans and sanctions that a named human authority recorded. */
  penalties?: ApiPenalty[];
  /** Staff only: reviews that a count of recorded sanctions asked a human authority for. */
  reviews_due?: ApiReview[];
  ai_notice: string;
  /** Present only on the response to the action that served notice. Shown once, never stored. */
  issued_response_token?: string;
  issued_notice_text?: string;
}

export interface ActionSpec {
  roles: string[];
  from_stages: string[];
  to_stage: string | null;
  note_required: boolean;
  params: string[];
}

export interface ActionMeta {
  actions: Record<string, ActionSpec>;
  checks: string[];
  sanction_kinds?: string[];
  review_thresholds?: Record<string, string>;
}

export interface LedgerRow {
  seq: number;
  ts: string;
  case_id: string | null;
  actor_id: string;
  actor_role: string;
  actor_kind: 'ai' | 'human' | 'system';
  action: string;
  payload: Record<string, unknown>;
  hash: string;
}

export interface VerifyResult {
  chain_valid: boolean;
  entries_checked: number;
  first_bad_seq: number | null;
  reason: string | null;
  projection_consistent: boolean;
  projection_problems: string[];
}

export interface ActionRequest {
  action: string;
  note?: string;
  check?: string;
  link_to?: string;
  party_ref?: string;
  party_role?: string;
  determination?: string;
  legal_basis?: string;
  sanction_kind?: string;
  amount_inr?: number;
  penalty_id?: number;
}
