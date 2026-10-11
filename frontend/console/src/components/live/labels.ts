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
  penalty_recorded: 'Challan or sanction recorded',
};

export const TRACK_LABEL: Record<string, string> = {
  criminal: 'Criminal track',
  civic: 'Civic track (challan, no FIR, not a flag)',
  departmental: 'Departmental track (no FIR)',
};

/** What each track can lead to, in plain words. */
export const TRACK_RULE: Record<string, string> = {
  civic:
    'A civic violation is not a crime. A human officer can issue a challan to each person decided to be a subject. No FIR can be registered, and nothing counts it as a flag.',
  departmental:
    'Official misconduct that is not an offence in itself. A competent authority can record a sanction against each person decided to be a subject, only after notice and a hearing. No FIR can be registered, and no software suspends, removes or fines anyone.',
};

export const SANCTION_LABEL: Record<string, string> = {
  challan: 'Challan',
  warning: 'Warning',
  fine: 'Fine',
  suspension: 'Suspension (interim)',
  licence_cancellation: 'Licence or contract cancellation',
  removal_order: 'Removal order (after inquiry)',
};

export const REVIEW_LABEL: Record<string, string> = {
  interim_suspension_review: 'Review whether to suspend (interim)',
  removal_inquiry_review: 'Review whether to open an inquiry for removal',
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
  issue_challan: 'Issue challan',
  impose_sanction: 'Record sanction',
  revoke_penalty: 'Revoke a challan or sanction',
  resolve_review: 'Answer a review request',
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
  physical_assault: 'physical assault',
  bribe_demand: 'demand for an illegal payment',
  obstructive_parking: 'parking that blocks a road',
  public_spitting: 'spitting in public',
  public_urination: 'urinating in public',
  waste_dumping_in_water: 'dumping waste in water',
  abuse_of_official_power: 'abuse of official power',
  private_agents_in_official_acts: 'private persons in official acts',
  official_misbehavior: 'official misbehaviour',
};

export const PARTY_ROLE_LABEL: Record<string, string> = {
  depicted_person: 'Person shown in the clip',
  uploader: 'Uploader',
  sharer: 'Sharer',
  recorder: 'Person who recorded it',
  performer_in_public_act: 'Person performing the public act',
  viewer_or_commenter: 'Viewer or commenter',
  vehicle_owner: 'Registered vehicle owner',
  public_servant: 'Public servant',
  private_agent_of_official: 'Private person acting for an official',
  contractor_or_licensee: 'Contractor or licensee',
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
  civic_violation: 'Civic violation',
  official_conduct: 'Official conduct',
};

/** The rule the server enforces for each scenario, in plain words. */
export const SCENARIO_RULE: Record<string, string> = {
  intimate_imagery_without_consent:
    'People shown in the video are victims, never suspects. The uploader, a sharer or the person who secretly recorded it can be a suspect.',
  public_indecent_act:
    'The person performing the act is the candidate suspect. Whoever filmed or posted it is not, unless they did something else wrong, such as extortion.',
  explicit_content_published:
    'Whoever published the material can be a suspect. A person who appears in it is judged separately in each role.',
  civic_violation:
    'The person who did it, or the registered owner of the vehicle, can be decided to be a subject. Whoever filmed or posted it never is.',
  official_conduct:
    'The public servant, a private person acting for them, or a contractor or licensee can be decided to be a subject. Whoever filmed or posted it, and anyone treated that way, never is.',
};
