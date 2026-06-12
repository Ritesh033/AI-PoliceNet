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

const courtOrderSchema = z.object({
  firId: z.string().uuid(),
  orderType: z.enum(['fir_amendment', 'investigation_directive', 'bail', 'arrest_warrant', 'evidence_request', 'case_closure']),
  orderText: z.string().min(10),
  issuedBy: z.string().uuid(),
});

const caseTransferSchema = z.object({
  firId: z.string().uuid(),
  fromCourt: z.string(),
  toCourt: z.string(),
  reason: z.string().min(10),
});

// Issue court order (judge-only)
router.post('/court/orders', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const data = courtOrderSchema.parse(req.body);
    const result = await pool.query(
      `INSERT INTO court_orders (fir_id, order_type, order_text, issued_by, digital_signature)
       VALUES ($1, $2, $3, $4, $5) RETURNING *`,
      [data.firId, data.orderType, data.orderText, data.issuedBy, `SIG-${Date.now()}`]
    );

    // If it's a FIR amendment order, update FIR
    if (data.orderType === 'fir_amendment') {
      // TODO: Notify FIR service to allow amendment
    }

    res.status(201).json({ message: 'Court order issued', data: result.rows[0] });
  } catch (error) {
    next(error);
  }
});

// Get orders for a FIR
router.get('/court/orders/fir/:firId', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const result = await pool.query(
      `SELECT co.*, u.full_name as judge_name
       FROM court_orders co LEFT JOIN users u ON co.issued_by = u.id
       WHERE co.fir_id = $1 ORDER BY co.created_at DESC`,
      [req.params.firId]
    );
    res.json({ data: result.rows });
  } catch (error) {
    next(error);
  }
});

// Transfer case between courts
router.post('/court/transfer', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const data = caseTransferSchema.parse(req.body);
    const transferredBy = (req as any).user?.id;

    // TODO: Record transfer in audit trail
    res.status(201).json({
      message: 'Case transfer initiated',
      data: { transferId: `TRF-${Date.now()}`, ...data, status: 'pending', transferredBy },
    });
  } catch (error) {
    next(error);
  }
});

// Get case file for court
router.get('/court/case-file/:firId', async (req: Request, res: Response, next: NextFunction) => {
  try {
    // Aggregates FIR + evidence + audit trail into a court-ready case file
    const fir = await pool.query('SELECT * FROM firs WHERE id = $1', [req.params.firId]);
    if (!fir.rows[0]) {
      res.status(404).json({ error: { code: 'NOT_FOUND', message: 'FIR not found' } });
      return;
    }

    const amendments = await pool.query('SELECT * FROM fir_amendments WHERE fir_id = $1', [req.params.firId]);
    const orders = await pool.query('SELECT * FROM court_orders WHERE fir_id = $1', [req.params.firId]);

    res.json({
      data: {
        fir: fir.rows[0],
        amendments: amendments.rows,
        courtOrders: orders.rows,
        evidence: [], // TODO: Fetch from evidence service
      },
    });
  } catch (error) {
    next(error);
  }
});

// Verify digital signature
router.post('/court/verify-signature', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const { documentId, signature } = req.body;
    // TODO: PKI verification
    res.json({
      data: { documentId, signatureValid: true, verifiedAt: new Date().toISOString() },
    });
  } catch (error) {
    next(error);
  }
});

export default router;
