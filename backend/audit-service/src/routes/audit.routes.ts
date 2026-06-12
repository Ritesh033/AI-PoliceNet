import { Router, Request, Response, NextFunction } from 'express';
import { Pool } from 'pg';

const pool = new Pool({
  host: process.env.POSTGRES_HOST || 'localhost',
  port: parseInt(process.env.POSTGRES_PORT || '5432', 10),
  database: process.env.POSTGRES_DB || 'ai_policenet',
  user: process.env.POSTGRES_USER || 'policenet_admin',
  password: process.env.POSTGRES_PASSWORD || 'changeme',
});

const router = Router();

// Record audit entry (append-only)
router.post('/audit/log', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const { action, resourceType, resourceId, details } = req.body;
    const userId = (req as any).user?.id;
    const ipAddress = req.ip;
    const userAgent = req.get('user-agent');

    const result = await pool.query(
      `INSERT INTO audit_logs (user_id, action, resource_type, resource_id, details, ip_address, user_agent)
       VALUES ($1, $2, $3, $4, $5, $6, $7) RETURNING *`,
      [userId, action, resourceType, resourceId, JSON.stringify(details || {}), ipAddress, userAgent]
    );

    res.status(201).json({ data: result.rows[0] });
  } catch (error) {
    next(error);
  }
});

// Query access logs
router.get('/audit/access-logs', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const page = Math.max(1, parseInt(req.query.page as string) || 1);
    const limit = Math.min(100, parseInt(req.query.limit as string) || 50);
    const offset = (page - 1) * limit;
    const userId = req.query.userId as string;
    const action = req.query.action as string;

    const conditions: string[] = [];
    const params: unknown[] = [];
    let idx = 1;

    if (userId) { conditions.push(`user_id = $${idx++}`); params.push(userId); }
    if (action) { conditions.push(`action = $${idx++}`); params.push(action); }

    const where = conditions.length > 0 ? `WHERE ${conditions.join(' AND ')}` : '';

    const countResult = await pool.query(`SELECT COUNT(*) FROM audit_logs ${where}`, params);
    const total = parseInt(countResult.rows[0].count, 10);

    params.push(limit, offset);
    const result = await pool.query(
      `SELECT al.*, u.full_name FROM audit_logs al LEFT JOIN users u ON al.user_id = u.id ${where} ORDER BY al.created_at DESC LIMIT $${idx++} OFFSET $${idx}`,
      params
    );

    res.json({ data: result.rows, pagination: { page, limit, total, totalPages: Math.ceil(total / limit) } });
  } catch (error) {
    next(error);
  }
});

// Get activity logs for a specific resource
router.get('/audit/resource/:type/:id', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const result = await pool.query(
      `SELECT al.*, u.full_name FROM audit_logs al LEFT JOIN users u ON al.user_id = u.id
       WHERE al.resource_type = $1 AND al.resource_id = $2 ORDER BY al.created_at ASC`,
      [req.params.type, req.params.id]
    );
    res.json({ data: result.rows });
  } catch (error) {
    next(error);
  }
});

export default router;
