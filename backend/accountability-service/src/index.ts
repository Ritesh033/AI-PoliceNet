import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import accountabilityRoutes from './routes/accountability.routes';
import winston from 'winston';

const logger = winston.createLogger({
  level: 'info',
  format: winston.format.combine(winston.format.timestamp(), winston.format.json()),
  defaultMeta: { service: 'accountability-service' },
  transports: [new winston.transports.Console()],
});

const PORT = parseInt(process.env.ACCOUNTABILITY_PORT || '8006', 10);
const app = express();

app.use(helmet());
app.use(cors());
app.use(express.json());

app.get('/health', (_req, res) => {
  res.json({ status: 'healthy', service: 'accountability-service', timestamp: new Date().toISOString() });
});

app.use(accountabilityRoutes);

app.use((err: any, _req: express.Request, res: express.Response, _next: express.NextFunction) => {
  logger.error('Accountability service error', { error: err.message });
  const statusCode = err.statusCode || 500;
  res.status(statusCode).json({
    error: { code: err.code || 'INTERNAL_ERROR', message: statusCode === 500 ? 'Internal server error' : err.message },
  });
});

app.listen(PORT, () => logger.info(`Accountability service running on port ${PORT}`));
export default app;
