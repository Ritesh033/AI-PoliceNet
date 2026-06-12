import { Router, Request, Response, NextFunction } from 'express';
import { z } from 'zod';
import { Pool } from 'pg';

const pool = new Pool({
  host: process.env.POSTGRES_HOST || 'localhost',
  port: parseInt(process.env.POSTGRES_PORT || '5432', 10),
  database: process.env.POSTGRES_DB || 'ai_policenet',
  user: process.env.POSTGRES_USER || 'policenet_admin',
  password: process.env.POSTGRES_PASSWORD || 'changeme',
});

const router = Router();

const assignOfficerSchema = z.object({
  firId: z.string().uuid(),
  officerId: z.string().uuid(),
  priority: z.enum(['normal', 'high', 'urgent']).default('normal'),
});

const timelineEventSchema = z.object({
  firId: z.string().uuid(),
  eventType: z.string(),
  description: z.string(),
  eventDate: z.string(),
  evidenceIds: z.array(z.string()).optional(),
});

// Assign officer to case
router.post('/investigations/assign', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const data = assignOfficerSchema.parse(req.body);
    const result = await pool.query(
      'UPDATE firs SET assigned_officer_id = $1, status = $2, updated_at = NOW() WHERE id = $3 RETURNING *',
      [data.officerId, 'investigation', data.firId]
    );
    if (!result.rows[0]) {
      res.status(404).json({ error: { code: 'NOT_FOUND', message: 'FIR not found' } });
      return;
    }
    res.json({ message: 'Officer assigned', data: result.rows[0] });
  } catch (error) {
    next(error);
  }
});

// Add timeline event
router.post('/investigations/timeline', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const data = timelineEventSchema.parse(req.body);
    const addedBy = (req as any).user?.id;

    // TODO: Store in investigation_timeline table
    res.status(201).json({
      message: 'Timeline event added',
      data: { timelineId: `TL-${Date.now()}`, ...data, addedBy },
    });
  } catch (error) {
    next(error);
  }
});

// Get investigation timeline
router.get('/investigations/:firId/timeline', async (req: Request, res: Response, next: NextFunction) => {
  try {
    // TODO: Query investigation timeline
    res.json({ data: { firId: req.params.firId, events: [] } });
  } catch (error) {
    next(error);
  }
});

// Get officer's assigned cases
router.get('/investigations/officer/:officerId', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const result = await pool.query(
      'SELECT * FROM firs WHERE assigned_officer_id = $1 ORDER BY created_at DESC',
      [req.params.officerId]
    );
    res.json({ data: result.rows });
  } catch (error) {
    next(error);
  }
});

// Link evidence to investigation
router.post('/investigations/:firId/evidence', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const { evidenceIds, notes } = req.body;
    const linkedBy = (req as any).user?.id;

    // TODO: Create evidence-investigation links
    res.status(201).json({
      message: 'Evidence linked to investigation',
      data: { firId: req.params.firId, evidenceIds, linkedBy },
    });
  } catch (error) {
    next(error);
  }
});

export default router;
