import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import { config } from './config';
import evidenceRoutes from './routes/evidence.routes';
import winston from 'winston';

const logger = winston.createLogger({
  level: 'info',
  format: winston.format.combine(winston.format.timestamp(), winston.format.json()),
  defaultMeta: { service: 'evidence-service' },
  transports: [new winston.transports.Console()],
});

const app = express();

app.use(helmet());
app.use(cors());
app.use(express.json({ limit: '50mb' }));

app.get('/health', (_req, res) => {
  res.json({ status: 'healthy', service: 'evidence-service', timestamp: new Date().toISOString() });
});

app.use(evidenceRoutes);

app.use((err: any, _req: express.Request, res: express.Response, _next: express.NextFunction) => {
  logger.error('Evidence service error', { error: err.message, stack: err.stack });
  const statusCode = err.statusCode || 500;
  res.status(statusCode).json({
    error: { code: err.code || 'INTERNAL_ERROR', message: statusCode === 500 ? 'Internal server error' : err.message },
  });
});

app.listen(config.port, () => {
  logger.info(`Evidence service running on port ${config.port}`);
});

export default app;
