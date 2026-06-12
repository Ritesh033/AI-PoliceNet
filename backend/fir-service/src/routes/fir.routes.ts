import { Router, Request, Response, NextFunction } from 'express';
import { z } from 'zod';
import * as firModel from '../models/fir';

const router = Router();

const createFirSchema = z.object({
  title: z.string().min(5).max(500),
  description: z.string().min(20),
  incidentDate: z.string().optional(),
  incidentLocation: z.string().optional(),
  incidentState: z.string().optional(),
  incidentDistrict: z.string().optional(),
  category: z.string().optional(),
  severity: z.enum(['low', 'medium', 'high', 'critical']).optional(),
});

const updateStatusSchema = z.object({
  status: z.enum(['registered', 'under_review', 'investigation', 'court_referred', 'resolved', 'closed', 'false_report']),
  reason: z.string().min(5),
});

const amendFirSchema = z.object({
  courtOrderId: z.string().min(1),
  amendmentDescription: z.string().min(10),
  approvedByJudge: z.string().uuid(),
});

// Create a new FIR
router.post('/fir', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const data = createFirSchema.parse(req.body);
    const complainantId = (req as any).user?.id;
    if (!complainantId) {
      res.status(401).json({ error: { code: 'UNAUTHORIZED', message: 'User ID required' } });
      return;
    }

    const fir = await firModel.createFir({ ...data, complainantId });

    // TODO: Publish fir.created event to Kafka
    res.status(201).json({
      message: 'FIR registered successfully',
      data: fir,
    });
  } catch (error) {
    next(error);
  }
});

// Get FIR by ID
router.get('/fir/:id', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const fir = await firModel.getFirById(req.params.id);
    if (!fir) {
      res.status(404).json({ error: { code: 'NOT_FOUND', message: 'FIR not found' } });
      return;
    }
    res.json({ data: fir });
  } catch (error) {
    next(error);
  }
});

// List FIRs with filters
router.get('/fir', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const page = Math.max(1, parseInt(req.query.page as string) || 1);
    const limit = Math.min(100, Math.max(1, parseInt(req.query.limit as string) || 20));

    const result = await firModel.listFirs({
      complainantId: req.query.complainantId as string,
      assignedOfficerId: req.query.assignedOfficerId as string,
      status: req.query.status as string,
      state: req.query.state as string,
      page,
      limit,
    });

    res.json({
      data: result.firs,
      pagination: {
        page,
        limit,
        total: result.total,
        totalPages: Math.ceil(result.total / limit),
      },
    });
  } catch (error) {
    next(error);
  }
});

// Get FIR audit trail (immutable history)
router.get('/fir/:id/audit', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const trail = await firModel.getFirAuditTrail(req.params.id);
    res.json({ data: trail });
  } catch (error) {
    next(error);
  }
});

// Update FIR status (authorized roles only — officer, inspector, admin)
router.put('/fir/:id/status', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const { status, reason } = updateStatusSchema.parse(req.body);
    const changedBy = (req as any).user?.id;

    const fir = await firModel.updateFirStatus(req.params.id, status, changedBy, reason);
    if (!fir) {
      res.status(404).json({ error: { code: 'NOT_FOUND', message: 'FIR not found' } });
      return;
    }

    // TODO: Publish fir.statusChanged event to Kafka
    res.json({ message: 'FIR status updated', data: fir });
  } catch (error) {
    next(error);
  }
});

// Amend FIR (requires court order)
router.post('/fir/:id/amend', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const data = amendFirSchema.parse(req.body);
    const amendedBy = (req as any).user?.id;

    const fir = await firModel.getFirById(req.params.id);
    if (!fir) {
      res.status(404).json({ error: { code: 'NOT_FOUND', message: 'FIR not found' } });
      return;
    }

    const amendment = await firModel.createFirAmendment({
      firId: req.params.id,
      ...data,
      amendedBy,
    });

    res.status(201).json({ message: 'FIR amendment recorded with court authorization', data: amendment });
  } catch (error) {
    next(error);
  }
});

export default router;
