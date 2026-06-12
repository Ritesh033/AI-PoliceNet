import { Pool } from 'pg';
import crypto from 'crypto';
import { config } from '../config';

export const pool = new Pool({
  host: config.postgres.host,
  port: config.postgres.port,
  database: config.postgres.database,
  user: config.postgres.user,
  password: config.postgres.password,
  max: 20,
});

export interface FIR {
  id: string;
  fir_number: string;
  complainant_id: string;
  title: string;
  description: string;
  incident_date: Date | null;
  incident_location: string | null;
  incident_state: string | null;
  incident_district: string | null;
  category: string | null;
  severity: string | null;
  status: string;
  assigned_officer_id: string | null;
  ai_risk_score: number | null;
  is_ai_generated: boolean;
  created_at: Date;
  updated_at: Date;
}

function generateFirNumber(state: string = 'XX', district: string = 'XXX'): string {
  const year = new Date().getFullYear();
  const seq = crypto.randomInt(100000, 999999);
  return `FIR-${state.toUpperCase().slice(0, 2)}-${district.toUpperCase().slice(0, 3)}-${year}-${seq}`;
}

export async function createFir(data: {
  complainantId: string;
  title: string;
  description: string;
  incidentDate?: string;
  incidentLocation?: string;
  incidentState?: string;
  incidentDistrict?: string;
  category?: string;
  severity?: string;
  isAiGenerated?: boolean;
}): Promise<FIR> {
  const firNumber = generateFirNumber(data.incidentState, data.incidentDistrict);

  const result = await pool.query(
    `INSERT INTO firs (fir_number, complainant_id, title, description, incident_date,
      incident_location, incident_state, incident_district, category, severity, is_ai_generated)
     VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
     RETURNING *`,
    [
      firNumber, data.complainantId, data.title, data.description,
      data.incidentDate || null, data.incidentLocation || null,
      data.incidentState || null, data.incidentDistrict || null,
      data.category || null, data.severity || null,
      data.isAiGenerated || false,
    ]
  );
  return result.rows[0];
}

export async function getFirById(id: string): Promise<FIR | null> {
  const result = await pool.query('SELECT * FROM firs WHERE id = $1', [id]);
  return result.rows[0] || null;
}

export async function getFirByNumber(firNumber: string): Promise<FIR | null> {
  const result = await pool.query('SELECT * FROM firs WHERE fir_number = $1', [firNumber]);
  return result.rows[0] || null;
}

export async function listFirs(filters: {
  complainantId?: string;
  assignedOfficerId?: string;
  status?: string;
  state?: string;
  page: number;
  limit: number;
}): Promise<{ firs: FIR[]; total: number }> {
  const conditions: string[] = [];
  const params: unknown[] = [];
  let paramIdx = 1;

  if (filters.complainantId) {
    conditions.push(`complainant_id = $${paramIdx++}`);
    params.push(filters.complainantId);
  }
  if (filters.assignedOfficerId) {
    conditions.push(`assigned_officer_id = $${paramIdx++}`);
    params.push(filters.assignedOfficerId);
  }
  if (filters.status) {
    conditions.push(`status = $${paramIdx++}`);
    params.push(filters.status);
  }
  if (filters.state) {
    conditions.push(`incident_state = $${paramIdx++}`);
    params.push(filters.state);
  }

  const where = conditions.length > 0 ? `WHERE ${conditions.join(' AND ')}` : '';
  const offset = (filters.page - 1) * filters.limit;

  const countResult = await pool.query(`SELECT COUNT(*) FROM firs ${where}`, params);
  const total = parseInt(countResult.rows[0].count, 10);

  params.push(filters.limit, offset);
  const result = await pool.query(
    `SELECT * FROM firs ${where} ORDER BY created_at DESC LIMIT $${paramIdx++} OFFSET $${paramIdx}`,
    params
  );

  return { firs: result.rows, total };
}

export async function updateFirStatus(
  firId: string,
  newStatus: string,
  changedBy: string,
  reason: string
): Promise<FIR | null> {
  const client = await pool.connect();
  try {
    await client.query('BEGIN');

    const current = await client.query('SELECT status FROM firs WHERE id = $1 FOR UPDATE', [firId]);
    if (!current.rows[0]) {
      await client.query('ROLLBACK');
      return null;
    }

    const previousStatus = current.rows[0].status;

    // Record status change in audit trail
    await client.query(
      `INSERT INTO fir_status_history (fir_id, previous_status, new_status, changed_by, reason)
       VALUES ($1, $2, $3, $4, $5)`,
      [firId, previousStatus, newStatus, changedBy, reason]
    );

    const result = await client.query(
      `UPDATE firs SET status = $1, updated_at = NOW() WHERE id = $2 RETURNING *`,
      [newStatus, firId]
    );

    await client.query('COMMIT');
    return result.rows[0];
  } catch (error) {
    await client.query('ROLLBACK');
    throw error;
  } finally {
    client.release();
  }
}

export async function getFirAuditTrail(firId: string): Promise<unknown[]> {
  const result = await pool.query(
    `SELECT fsh.*, u.full_name as changed_by_name
     FROM fir_status_history fsh
     LEFT JOIN users u ON fsh.changed_by = u.id
     WHERE fsh.fir_id = $1
     ORDER BY fsh.created_at ASC`,
    [firId]
  );
  return result.rows;
}

export async function createFirAmendment(data: {
  firId: string;
  courtOrderId: string;
  amendmentDescription: string;
  amendedBy: string;
  approvedByJudge: string;
}): Promise<unknown> {
  const result = await pool.query(
    `INSERT INTO fir_amendments (fir_id, court_order_id, amendment_description, amended_by, approved_by_judge)
     VALUES ($1, $2, $3, $4, $5) RETURNING *`,
    [data.firId, data.courtOrderId, data.amendmentDescription, data.amendedBy, data.approvedByJudge]
  );
  return result.rows[0];
}
