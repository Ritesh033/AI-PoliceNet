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
  | 'linked';

export interface ApiItem {
  id: number;
  kind: 'evidence' | 'response' | 'advisory' | 'context_finding';
  label: string;
  outcome: 'supports_flag' | 'undermines_flag' | 'inconclusive' | null;
  description: string;
  sha256: string | null;
  preview_withheld: boolean;
  late: boolean;
  added_by: string;
  added_at: string;
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
  signals?: string[];
  behaviors: string[];
  situation: string[];
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
  ai_notice: string;
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
}
