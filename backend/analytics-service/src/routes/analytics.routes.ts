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

// Dashboard overview
router.get('/analytics/dashboard', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const [firCount, officerCount, userCount, pendingMisconduct] = await Promise.all([
      pool.query('SELECT COUNT(*) as count FROM firs'),
      pool.query('SELECT COUNT(*) as count FROM officers WHERE is_active = true'),
      pool.query('SELECT COUNT(*) as count FROM users WHERE is_active = true'),
      pool.query("SELECT COUNT(*) as count FROM misconduct_reports WHERE status = 'pending'"),
    ]);

    const firByStatus = await pool.query(
      'SELECT status, COUNT(*) as count FROM firs GROUP BY status'
    );

    res.json({
      data: {
        totalFirs: parseInt(firCount.rows[0].count, 10),
        activeOfficers: parseInt(officerCount.rows[0].count, 10),
        registeredUsers: parseInt(userCount.rows[0].count, 10),
        pendingMisconductReports: parseInt(pendingMisconduct.rows[0].count, 10),
        firsByStatus: firByStatus.rows,
      },
    });
  } catch (error) {
    next(error);
  }
});

// FIR trends
router.get('/analytics/trends/firs', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const days = parseInt(req.query.days as string) || 30;
    const result = await pool.query(
      `SELECT DATE(created_at) as date, COUNT(*) as count
       FROM firs WHERE created_at >= NOW() - INTERVAL '1 day' * $1
       GROUP BY DATE(created_at) ORDER BY date`,
      [days]
    );
    res.json({ data: result.rows });
  } catch (error) {
    next(error);
  }
});

// Crime heatmap data
router.get('/analytics/heatmaps/crime', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const result = await pool.query(
      `SELECT incident_state, incident_district, COUNT(*) as count
       FROM firs WHERE incident_state IS NOT NULL
       GROUP BY incident_state, incident_district ORDER BY count DESC`
    );
    res.json({ data: result.rows });
  } catch (error) {
    next(error);
  }
});

// Officer performance analytics
router.get('/analytics/officers/performance', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const result = await pool.query(
      `SELECT o.id, u.full_name, o.badge_number, o.integrity_score,
              COUNT(f.id) as assigned_cases,
              COUNT(CASE WHEN f.status = 'resolved' THEN 1 END) as resolved_cases
       FROM officers o
       JOIN users u ON o.user_id = u.id
       LEFT JOIN firs f ON o.id = f.assigned_officer_id
       WHERE o.is_active = true
       GROUP BY o.id, u.full_name, o.badge_number, o.integrity_score
       ORDER BY o.integrity_score DESC`
    );
    res.json({ data: result.rows });
  } catch (error) {
    next(error);
  }
});

// Generate report
router.get('/analytics/reports/:type', async (req: Request, res: Response, next: NextFunction) => {
  try {
    // TODO: Generate PDF/CSV reports based on type
    res.json({
      message: 'Report generation — connect to report engine',
      data: { reportType: req.params.type, status: 'pending' },
    });
  } catch (error) {
    next(error);
  }
});

export default router;
