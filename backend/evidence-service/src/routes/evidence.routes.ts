import { Router, Request, Response, NextFunction } from 'express';
import { z } from 'zod';
import * as evidenceService from '../services/evidence.service';

const router = Router();

const uploadEvidenceSchema = z.object({
  firId: z.string().uuid(),
  fileType: z.enum(['video', 'audio', 'image', 'document']),
  fileFormat: z.string(),
  fileSizeBytes: z.number().positive(),
  metadata: z.object({
    captureDate: z.string().optional(),
    captureLocation: z.object({
      latitude: z.number(),
      longitude: z.number(),
    }).optional(),
    deviceInfo: z.string().optional(),
    durationSeconds: z.number().optional(),
    resolution: z.string().optional(),
  }).optional(),
});

const reviewSchema = z.object({
  decision: z.enum(['verify_permanent', 'reject']),
  reason: z.string().min(5),
});

// Upload evidence
router.post('/evidence/upload', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const data = uploadEvidenceSchema.parse(req.body);
    const uploadedBy = (req as any).user?.id;

    const evidenceId = evidenceService.generateEvidenceId();
    const reviewDeadline = evidenceService.calculateReviewDeadline();

    // In production: file would be read from multipart upload, hashed, stored in S3
    const evidence: Partial<evidenceService.EvidenceDocument> = {
      evidenceId,
      firId: data.firId,
      uploadedBy,
      fileType: data.fileType,
      fileFormat: data.fileFormat,
      fileSizeBytes: data.fileSizeBytes,
      status: 'temporary',
      reviewDeadline,
      metadata: data.metadata || {},
      chainOfCustody: [
        evidenceService.createChainOfCustodyEntry('uploaded', uploadedBy, 'Evidence uploaded by citizen'),
      ],
      relatedEvidenceCount: 1,
      createdAt: new Date(),
      updatedAt: new Date(),
    };

    // TODO: Store in MongoDB and publish to Kafka
    // TODO: Register hash on blockchain

    res.status(201).json({
      message: 'Evidence uploaded successfully. Marked as temporary — you have 5 days to upload complete evidence.',
      data: {
        evidenceId,
        status: 'temporary',
        reviewDeadline: reviewDeadline.toISOString(),
        legalNotice: 'This evidence is flagged as temporary FIVR. Upload complete evidence within the review period.',
      },
    });
  } catch (error) {
    next(error);
  }
});

// Get evidence by ID
router.get('/evidence/:id', async (req: Request, res: Response, next: NextFunction) => {
  try {
    // TODO: Query MongoDB for evidence document
    res.json({
      data: {
        evidenceId: req.params.id,
        message: 'Evidence retrieval — connect to MongoDB',
      },
    });
  } catch (error) {
    next(error);
  }
});

// Get chain of custody
router.get('/evidence/:id/chain-of-custody', async (req: Request, res: Response, next: NextFunction) => {
  try {
    // TODO: Query MongoDB for chain of custody
    res.json({
      data: {
        evidenceId: req.params.id,
        chainOfCustody: [],
        message: 'Chain of custody retrieval — connect to MongoDB',
      },
    });
  } catch (error) {
    next(error);
  }
});

// Verify evidence hash
router.post('/evidence/:id/verify', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const { hash } = req.body;
    // TODO: Compare provided hash with stored hash and blockchain record
    res.json({
      data: {
        evidenceId: req.params.id,
        hashMatch: true,
        blockchainVerified: true,
        message: 'Hash verification — connect to blockchain',
      },
    });
  } catch (error) {
    next(error);
  }
});

// Moderator review evidence (verify or reject)
router.post('/evidence/:id/review', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const { decision, reason } = reviewSchema.parse(req.body);
    const reviewedBy = (req as any).user?.id;

    const newStatus = decision === 'verify_permanent' ? 'verified_permanent' : 'rejected';

    // TODO: Update in MongoDB, add chain of custody entry, publish Kafka event

    res.json({
      message: `Evidence ${decision === 'verify_permanent' ? 'verified as permanent' : 'rejected'}`,
      data: {
        evidenceId: req.params.id,
        status: newStatus,
        reviewedBy,
        reason,
      },
    });
  } catch (error) {
    next(error);
  }
});

// Search evidence
router.get('/evidence/search', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const { firId, status, fileType, query } = req.query;
    // TODO: Search via Elasticsearch
    res.json({
      data: [],
      pagination: { page: 1, limit: 20, total: 0, totalPages: 0 },
    });
  } catch (error) {
    next(error);
  }
});

export default router;
