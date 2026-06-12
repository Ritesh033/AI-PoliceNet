import crypto from 'crypto';
import { config } from '../config';

export interface EvidenceDocument {
  evidenceId: string;
  firId: string;
  uploadedBy: string;
  fileHash: string;
  fileType: 'video' | 'audio' | 'image' | 'document';
  fileFormat: string;
  fileSizeBytes: number;
  storagePath: string;
  status: 'temporary' | 'under_review' | 'verified_permanent' | 'rejected';
  reviewDeadline: Date;
  metadata: {
    captureDate?: string;
    captureLocation?: { latitude: number; longitude: number };
    deviceInfo?: string;
    durationSeconds?: number;
    resolution?: string;
  };
  aiAnalysis?: {
    authenticityScore?: number;
    deepfakeProbability?: number;
    contentTags?: string[];
    violenceDetected?: boolean;
    threatLevel?: string;
  };
  chainOfCustody: Array<{
    action: string;
    actorId: string;
    timestamp: Date;
    details: string;
  }>;
  blockchainTxId?: string;
  relatedEvidenceCount: number;
  createdAt: Date;
  updatedAt: Date;
}

export function generateEvidenceId(): string {
  const timestamp = Date.now().toString(36);
  const random = crypto.randomBytes(6).toString('hex');
  return `EVD-${timestamp}-${random}`.toUpperCase();
}

export function computeFileHash(buffer: Buffer): string {
  return crypto.createHash('sha256').update(buffer).digest('hex');
}

export function determineFileType(mimeType: string): 'video' | 'audio' | 'image' | 'document' {
  if (mimeType.startsWith('video/')) return 'video';
  if (mimeType.startsWith('audio/')) return 'audio';
  if (mimeType.startsWith('image/')) return 'image';
  return 'document';
}

export function calculateReviewDeadline(): Date {
  const deadline = new Date();
  deadline.setDate(deadline.getDate() + config.evidence.reviewPeriodDays);
  return deadline;
}

/**
 * Evidence Review Workflow:
 *
 * 1. Upload → Evidence receives SHA-256 hash, marked as "temporary"
 * 2. User notified: 3-5 day window to upload complete evidence
 * 3. If user uploads 3+ videos of same event → auto-convert to "verified_permanent"
 * 4. Moderator + AI verify authenticity
 * 5. Verified → "verified_permanent" (used in investigation/court)
 * 6. Rejected → marked with reason, preserved for audit
 *
 * Same-day single upload: flagged as "temporary FIVR" with legal notice to user
 */
export function shouldAutoPromoteToPermanent(relatedCount: number): boolean {
  return relatedCount >= config.evidence.permanentThreshold;
}

export function createChainOfCustodyEntry(
  action: string,
  actorId: string,
  details: string
): EvidenceDocument['chainOfCustody'][0] {
  return {
    action,
    actorId,
    timestamp: new Date(),
    details,
  };
}
