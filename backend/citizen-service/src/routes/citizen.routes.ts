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

const updateProfileSchema = z.object({
  fullName: z.string().min(2).max(255).optional(),
  address: z.string().optional(),
  state: z.string().optional(),
  district: z.string().optional(),
});

const complaintSchema = z.object({
  title: z.string().min(5).max(500),
  description: z.string().min(20),
  category: z.string().optional(),
  incidentDate: z.string().optional(),
  incidentLocation: z.string().optional(),
  severity: z.enum(['low', 'medium', 'high', 'critical']).optional(),
});

// Get citizen profile
router.get('/citizens/profile', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const userId = (req as any).user?.id;
    const result = await pool.query(
      'SELECT id, registration_id, email, phone, full_name, address, state, district, user_type, is_verified, created_at FROM users WHERE id = $1',
      [userId]
    );
    if (!result.rows[0]) {
      res.status(404).json({ error: { code: 'NOT_FOUND', message: 'Profile not found' } });
      return;
    }
    res.json({ data: result.rows[0] });
  } catch (error) {
    next(error);
  }
});

// Update citizen profile
router.put('/citizens/profile', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const data = updateProfileSchema.parse(req.body);
    const userId = (req as any).user?.id;
    const fields: string[] = [];
    const values: unknown[] = [];
    let idx = 1;

    if (data.fullName) { fields.push(`full_name = $${idx++}`); values.push(data.fullName); }
    if (data.address) { fields.push(`address = $${idx++}`); values.push(data.address); }
    if (data.state) { fields.push(`state = $${idx++}`); values.push(data.state); }
    if (data.district) { fields.push(`district = $${idx++}`); values.push(data.district); }

    if (fields.length === 0) {
      res.status(400).json({ error: { code: 'BAD_REQUEST', message: 'No fields to update' } });
      return;
    }

    fields.push(`updated_at = NOW()`);
    values.push(userId);

    const result = await pool.query(
      `UPDATE users SET ${fields.join(', ')} WHERE id = $${idx} RETURNING id, registration_id, email, phone, full_name, address, state, district`,
      values
    );
    res.json({ message: 'Profile updated', data: result.rows[0] });
  } catch (error) {
    next(error);
  }
});

// File a complaint
router.post('/citizens/complaints', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const data = complaintSchema.parse(req.body);
    const userId = (req as any).user?.id;

    // Complaints generate a pre-FIR record; they can be promoted to FIR by officers
    const result = await pool.query(
      `INSERT INTO firs (fir_number, complainant_id, title, description, incident_date, incident_location, category, severity, status)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'registered') RETURNING *`,
      [
        `CMP-${Date.now().toString(36).toUpperCase()}`,
        userId, data.title, data.description,
        data.incidentDate || null, data.incidentLocation || null,
        data.category || null, data.severity || null,
      ]
    );

    res.status(201).json({ message: 'Complaint filed successfully', data: result.rows[0] });
  } catch (error) {
    next(error);
  }
});

// List citizen's complaints
router.get('/citizens/complaints', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const userId = (req as any).user?.id;
    const page = Math.max(1, parseInt(req.query.page as string) || 1);
    const limit = Math.min(100, parseInt(req.query.limit as string) || 20);
    const offset = (page - 1) * limit;

    const countResult = await pool.query('SELECT COUNT(*) FROM firs WHERE complainant_id = $1', [userId]);
    const total = parseInt(countResult.rows[0].count, 10);

    const result = await pool.query(
      'SELECT * FROM firs WHERE complainant_id = $1 ORDER BY created_at DESC LIMIT $2 OFFSET $3',
      [userId, limit, offset]
    );

    res.json({
      data: result.rows,
      pagination: { page, limit, total, totalPages: Math.ceil(total / limit) },
    });
  } catch (error) {
    next(error);
  }
});

export default router;
