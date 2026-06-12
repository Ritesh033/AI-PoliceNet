import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import investigationRoutes from './routes/investigation.routes';
import winston from 'winston';

const logger = winston.createLogger({
  level: 'info',
  format: winston.format.combine(winston.format.timestamp(), winston.format.json()),
  defaultMeta: { service: 'investigation-service' },
  transports: [new winston.transports.Console()],
});

const PORT = parseInt(process.env.INVESTIGATION_PORT || '8008', 10);
const app = express();
app.use(helmet());
app.use(cors());
app.use(express.json());

app.get('/health', (_req, res) => {
  res.json({ status: 'healthy', service: 'investigation-service', timestamp: new Date().toISOString() });
});
app.use(investigationRoutes);

app.use((err: any, _req: express.Request, res: express.Response, _next: express.NextFunction) => {
  logger.error('Investigation service error', { error: err.message });
  res.status(err.statusCode || 500).json({ error: { code: err.code || 'INTERNAL_ERROR', message: err.message } });
});

app.listen(PORT, () => logger.info(`Investigation service running on port ${PORT}`));
export default app;
