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

const misconductSchema = z.object({
  officerId: z.string().uuid(),
  reportType: z.enum(['false_fir', 'misconduct', 'corruption', 'abuse_of_power', 'evidence_tampering', 'phone_seizure', 'misbehavior']),
  description: z.string().min(20),
  evidenceIds: z.array(z.string().uuid()).optional(),
});

const fineSchema = z.object({
  officerId: z.string().uuid(),
  misconductReportId: z.string().uuid(),
  fineAmount: z.number().positive(),
  reason: z.string().min(10),
});

const disciplinarySchema = z.object({
  officerId: z.string().uuid(),
  actionType: z.enum(['warning', 'suspension', 'fine', 'demotion', 'termination', 'inquiry']),
  description: z.string().min(10),
  effectiveDate: z.string(),
});

// Get officer integrity score
router.get('/accountability/officers/:id/score', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const result = await pool.query(
      `SELECT o.id, o.badge_number, o.batch_number, o.department, o.designation, o.rank,
              o.posting_location, o.integrity_score, u.full_name
       FROM officers o JOIN users u ON o.user_id = u.id
       WHERE o.id = $1`,
      [req.params.id]
    );
    if (!result.rows[0]) {
      res.status(404).json({ error: { code: 'NOT_FOUND', message: 'Officer not found' } });
      return;
    }
    res.json({ data: result.rows[0] });
  } catch (error) {
    next(error);
  }
});

// Get officer review history
router.get('/accountability/officers/:id/reviews', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const misconduct = await pool.query(
      'SELECT * FROM misconduct_reports WHERE officer_id = $1 ORDER BY created_at DESC',
      [req.params.id]
    );
    const fines = await pool.query(
      'SELECT * FROM officer_fines WHERE officer_id = $1 ORDER BY created_at DESC',
      [req.params.id]
    );
    const disciplinary = await pool.query(
      'SELECT * FROM disciplinary_actions WHERE officer_id = $1 ORDER BY created_at DESC',
      [req.params.id]
    );

    res.json({
      data: {
        misconductReports: misconduct.rows,
        fines: fines.rows,
        disciplinaryActions: disciplinary.rows,
      },
    });
  } catch (error) {
    next(error);
  }
});

// Report misconduct
router.post('/accountability/misconduct', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const data = misconductSchema.parse(req.body);
    const reportedBy = (req as any).user?.id;

    const result = await pool.query(
      `INSERT INTO misconduct_reports (officer_id, reported_by, report_type, description, evidence_ids)
       VALUES ($1, $2, $3, $4, $5) RETURNING *`,
      [data.officerId, reportedBy, data.reportType, data.description, data.evidenceIds || []]
    );

    // TODO: Trigger AI analysis for pattern detection
    // TODO: Publish event to Kafka

    res.status(201).json({ message: 'Misconduct report filed', data: result.rows[0] });
  } catch (error) {
    next(error);
  }
});

// Issue fine for false FIR (authorized authority only)
router.post('/accountability/fines', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const data = fineSchema.parse(req.body);
    const authorizedBy = (req as any).user?.id;

    const client = await pool.connect();
    try {
      await client.query('BEGIN');

      // Record the fine
      const fine = await client.query(
        `INSERT INTO officer_fines (officer_id, misconduct_report_id, fine_amount, reason, authorized_by)
         VALUES ($1, $2, $3, $4, $5) RETURNING *`,
        [data.officerId, data.misconductReportId, data.fineAmount, data.reason, authorizedBy]
      );

      // Reduce integrity score
      const deduction = Math.min(data.fineAmount / 10000, 20); // Max 20 point deduction per fine
      await client.query(
        'UPDATE officers SET integrity_score = GREATEST(0, integrity_score - $1) WHERE id = $2',
        [deduction, data.officerId]
      );

      await client.query('COMMIT');
      res.status(201).json({ message: 'Fine issued', data: fine.rows[0] });
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  } catch (error) {
    next(error);
  }
});

// Disciplinary action
router.post('/accountability/disciplinary', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const data = disciplinarySchema.parse(req.body);
    const authorizedBy = (req as any).user?.id;

    const result = await pool.query(
      `INSERT INTO disciplinary_actions (officer_id, action_type, description, authorized_by, effective_date)
       VALUES ($1, $2, $3, $4, $5) RETURNING *`,
      [data.officerId, data.actionType, data.description, authorizedBy, data.effectiveDate]
    );

    res.status(201).json({ message: 'Disciplinary action recorded', data: result.rows[0] });
  } catch (error) {
    next(error);
  }
});

// Get all misconduct reports (for admin/oversight)
router.get('/accountability/misconduct', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const page = Math.max(1, parseInt(req.query.page as string) || 1);
    const limit = Math.min(100, parseInt(req.query.limit as string) || 20);
    const offset = (page - 1) * limit;
    const status = req.query.status as string;

    let query = 'SELECT mr.*, u.full_name as officer_name FROM misconduct_reports mr LEFT JOIN officers o ON mr.officer_id = o.id LEFT JOIN users u ON o.user_id = u.id';
    const params: unknown[] = [];

    if (status) {
      query += ' WHERE mr.status = $1';
      params.push(status);
    }

    const countResult = await pool.query(`SELECT COUNT(*) FROM misconduct_reports ${status ? 'WHERE status = $1' : ''}`, status ? [status] : []);
    const total = parseInt(countResult.rows[0].count, 10);

    params.push(limit, offset);
    query += ` ORDER BY mr.created_at DESC LIMIT $${params.length - 1} OFFSET $${params.length}`;

    const result = await pool.query(query, params);
    res.json({
      data: result.rows,
      pagination: { page, limit, total, totalPages: Math.ceil(total / limit) },
    });
  } catch (error) {
    next(error);
  }
});

export default router;
