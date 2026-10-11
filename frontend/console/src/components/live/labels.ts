import type { ApiItem, ApiStage } from '../../api/types';

export const API_STAGE_LABEL: Record<ApiStage, string> = {
  received: 'Received (temporary flag)',
  in_review: 'In review',
  referred: 'Referred',
  inquiry: 'Inquiry',
  fir_registered: 'FIR registered by officer',
  closed_no_action: 'Closed, no action',
  closed_by_court: 'Closed by court',
  linked: 'Linked to another case',
};

export const ACTION_LABEL: Record<string, string> = {
  assign: 'Assign to me',
  record_check: 'Record a check',
  request_context: 'Request more context',
  no_action: 'No action',
  refer: 'Refer',
  open_inquiry: 'Open inquiry',
  decline: 'Decline',
  register_fir: 'Register FIR',
  serve_notice: 'Record notice served',
  court_proceed: 'Court: matter proceeds',
  court_close: 'Court: close FIR',
  permit_fresh_registration: 'Court: permit fresh registration',
  link_supplementary: 'Link as supplementary info',
  resolve_appeal: 'Resolve appeal',
};

export const CONTEXT_KEYS: ReadonlyArray<{ key: string; label: string }> = [
  { key: 'media_source', label: 'Film, show or skit match' },
  { key: 'edit_detection', label: 'Edited or partial video' },
  { key: 'full_context', label: 'Full original context' },
  { key: 'cross_platform_copies', label: 'Other copies of the clip' },
];

export const OUTCOME_LABEL: Record<NonNullable<ApiItem['outcome']>, string> = {
  supports_flag: 'Supports the flag',
  undermines_flag: 'Undermines the flag',
  inconclusive: 'Inconclusive',
};

export const BEHAVIOR_LABEL: Record<string, string> = {
  casual_profanity: 'casual profanity',
  insult: 'insult',
  criticism: 'criticism',
  false_statement: 'false statement',
  aggressive_abuse: 'aggressive abuse',
  threat: 'threat',
  extortion: 'extortion',
  fraud: 'fraud',
  impersonation: 'impersonation',
  sexual_content: 'sexual content',
  sexual_harassment: 'sexual harassment',
  non_consensual_imagery: 'non-consensual imagery',
  child_involved: 'child involved',
  incitement_to_violence: 'incitement to violence',
  targeted_hate: 'targeted hate',
  self_admission: 'self-admission',
};
