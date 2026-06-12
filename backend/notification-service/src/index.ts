import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import notificationRoutes from './routes/notification.routes';
import winston from 'winston';

const logger = winston.createLogger({
  level: 'info',
  format: winston.format.combine(winston.format.timestamp(), winston.format.json()),
  defaultMeta: { service: 'notification-service' },
  transports: [new winston.transports.Console()],
});

const PORT = parseInt(process.env.NOTIFICATION_PORT || '8007', 10);
const app = express();
app.use(helmet());
app.use(cors());
app.use(express.json());

app.get('/health', (_req, res) => {
  res.json({ status: 'healthy', service: 'notification-service', timestamp: new Date().toISOString() });
});
app.use(notificationRoutes);

app.use((err: any, _req: express.Request, res: express.Response, _next: express.NextFunction) => {
  logger.error('Notification service error', { error: err.message });
  res.status(err.statusCode || 500).json({ error: { code: err.code || 'INTERNAL_ERROR', message: err.message } });
});

app.listen(PORT, () => logger.info(`Notification service running on port ${PORT}`));
export default app;
