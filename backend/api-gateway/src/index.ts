import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import { config } from './config';
import { defaultRateLimiter } from './middleware/rate-limiter';
import { errorHandler } from './middleware/error-handler';
import { requestLogger } from './middleware/request-logger';
import { logger } from './middleware/logger';
import healthRoutes from './routes/health';
import proxyRoutes from './routes/proxy';

const app = express();

// Security
app.use(helmet());
app.use(cors({
  origin: process.env.CORS_ORIGINS?.split(',') || ['http://localhost:3000', 'http://localhost:3001', 'http://localhost:3002'],
  credentials: true,
}));

// Middleware
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true }));
app.use(requestLogger);
app.use(defaultRateLimiter);

// Routes
app.use(healthRoutes);
app.use(proxyRoutes);

// Error handling
app.use(errorHandler);

app.listen(config.port, () => {
  logger.info(`API Gateway running on port ${config.port}`, {
    environment: config.nodeEnv,
  });
});

export default app;
