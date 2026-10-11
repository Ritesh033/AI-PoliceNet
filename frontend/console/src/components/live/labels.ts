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
  determine_party: 'Decide who is who',
  request_identification: 'Record identification request',
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

export const PARTY_ROLE_LABEL: Record<string, string> = {
  depicted_person: 'Person shown in the clip',
  uploader: 'Uploader',
  sharer: 'Sharer',
  recorder: 'Person who recorded it',
  performer_in_public_act: 'Person performing the public act',
  viewer_or_commenter: 'Viewer or commenter',
};

export const DETERMINATION_LABEL: Record<string, string> = {
  subject: 'Subject',
  victim: 'Victim',
  witness: 'Witness',
  not_involved: 'Not involved',
};

export const SCENARIO_LABEL: Record<string, string> = {
  intimate_imagery_without_consent: 'Intimate imagery shared without consent',
  public_indecent_act: 'Public indecent act',
  explicit_content_published: 'Explicit content published by those who made or share it',
};

/** The rule the server enforces for each scenario, in plain words. */
export const SCENARIO_RULE: Record<string, string> = {
  intimate_imagery_without_consent:
    'People shown in the video are victims, never suspects. The uploader, a sharer or the person who secretly recorded it can be a suspect.',
  public_indecent_act:
    'The person performing the act is the candidate suspect. Whoever filmed or posted it is not, unless they did something else wrong, such as extortion.',
  explicit_content_published:
    'Whoever published the material can be a suspect. A person who appears in it is judged separately in each role.',
};
