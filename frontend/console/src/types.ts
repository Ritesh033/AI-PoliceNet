export type CategoryId = 'threat' | 'ncii' | 'scam' | 'hate' | 'manipulated';
export type IncidentCategory = CategoryId | 'conduct';
export type Period = '24h' | '7d' | '30d';
export type Priority = 'urgent' | 'high' | 'routine';
export type Stage = 'awaiting' | 'in_review' | 'referred' | 'closed';
export type CaseKind = 'social' | 'conduct';
export type Triage = 'urgent' | 'review' | 'none';
export type ReviewLane =
  | 'Priority review'
  | 'Evidence review'
  | 'Supervisor review'
  | 'Legal review'
  | 'Standard review';

export interface AuditEntry {
  at: number;
  actor: string;
  action: string;
  note?: string;
}

export interface Evidence {
  /** SHA-256 style digest of the (sample) captured item. */
  hash: string;
  capturedAt: number;
  /** Opaque sample locator. Never a real URL. */
  locator: string;
  /** Sensitive material is never rendered in the console. */
  previewWithheld: boolean;
}

export interface Incident {
  id: string;
  kind: CaseKind;
  category: IncidentCategory;
  title: string;
  summary: string;
  priority: Priority;
  lane: ReviewLane;
  stage: Stage;
  /** 0..1, model confidence that the item matches the flagged category. */
  confidence: number;
  source: string;
  platform?: string;
  state: string;
  district: string;
  receivedAt: number;
  dueAt: number;
  referredAt?: number;
  contextRequested?: boolean;
  signals: string[];
  evidence: Evidence;
  nextStep: string;
  history: AuditEntry[];
}

export interface Bucket {
  start: number;
  label: string;
  counts: Record<CategoryId, number>;
  total: number;
}

export interface PeriodSeries {
  buckets: Bucket[];
  /** Total for the immediately preceding period of the same length. */
  previousTotal: number;
}

export interface FeedEvent {
  id: string;
  at: number;
  tone: 'alert' | 'queue' | 'system';
  text: string;
}
