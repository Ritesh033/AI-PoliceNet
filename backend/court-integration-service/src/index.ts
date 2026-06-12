import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import courtRoutes from './routes/court.routes';
import winston from 'winston';

const logger = winston.createLogger({
  level: 'info',
  format: winston.format.combine(winston.format.timestamp(), winston.format.json()),
  defaultMeta: { service: 'court-integration-service' },
  transports: [new winston.transports.Console()],
});

const PORT = parseInt(process.env.COURT_PORT || '8009', 10);
const app = express();
app.use(helmet());
app.use(cors());
app.use(express.json());

app.get('/health', (_req, res) => {
  res.json({ status: 'healthy', service: 'court-integration-service', timestamp: new Date().toISOString() });
});
app.use(courtRoutes);

app.use((err: any, _req: express.Request, res: express.Response, _next: express.NextFunction) => {
  logger.error('Court service error', { error: err.message });
  res.status(err.statusCode || 500).json({ error: { code: err.code || 'INTERNAL_ERROR', message: err.message } });
});

app.listen(PORT, () => logger.info(`Court integration service running on port ${PORT}`));
export default app;
