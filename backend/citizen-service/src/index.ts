import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import citizenRoutes from './routes/citizen.routes';
import winston from 'winston';

const logger = winston.createLogger({
  level: 'info',
  format: winston.format.combine(winston.format.timestamp(), winston.format.json()),
  defaultMeta: { service: 'citizen-service' },
  transports: [new winston.transports.Console()],
});

const PORT = parseInt(process.env.CITIZEN_PORT || '8002', 10);
const app = express();

app.use(helmet());
app.use(cors());
app.use(express.json());

app.get('/health', (_req, res) => {
  res.json({ status: 'healthy', service: 'citizen-service', timestamp: new Date().toISOString() });
});

app.use(citizenRoutes);

app.use((err: any, _req: express.Request, res: express.Response, _next: express.NextFunction) => {
  logger.error('Citizen service error', { error: err.message });
  const statusCode = err.statusCode || 500;
  res.status(statusCode).json({
    error: { code: err.code || 'INTERNAL_ERROR', message: statusCode === 500 ? 'Internal server error' : err.message },
  });
});

app.listen(PORT, () => logger.info(`Citizen service running on port ${PORT}`));
export default app;
