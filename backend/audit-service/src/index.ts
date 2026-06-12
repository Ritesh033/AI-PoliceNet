import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import auditRoutes from './routes/audit.routes';
import winston from 'winston';

const logger = winston.createLogger({
  level: 'info',
  format: winston.format.combine(winston.format.timestamp(), winston.format.json()),
  defaultMeta: { service: 'audit-service' },
  transports: [new winston.transports.Console()],
});

const PORT = parseInt(process.env.AUDIT_PORT || '8011', 10);
const app = express();
app.use(helmet());
app.use(cors());
app.use(express.json());

app.get('/health', (_req, res) => {
  res.json({ status: 'healthy', service: 'audit-service', timestamp: new Date().toISOString() });
});
app.use(auditRoutes);

app.use((err: any, _req: express.Request, res: express.Response, _next: express.NextFunction) => {
  logger.error('Audit service error', { error: err.message });
  res.status(err.statusCode || 500).json({ error: { code: err.code || 'INTERNAL_ERROR', message: err.message } });
});

app.listen(PORT, () => logger.info(`Audit service running on port ${PORT}`));
export default app;
