import { Request, Response, NextFunction } from 'express';
import { logger } from './logger';

interface AppError extends Error {
  statusCode?: number;
  code?: string;
  details?: unknown;
}

export function errorHandler(err: AppError, req: Request, res: Response, _next: NextFunction): void {
  const statusCode = err.statusCode || 500;
  const code = err.code || 'INTERNAL_ERROR';

  logger.error('Request error', {
    method: req.method,
    path: req.path,
    statusCode,
    code,
    message: err.message,
    stack: process.env.NODE_ENV === 'development' ? err.stack : undefined,
  });

  res.status(statusCode).json({
    error: {
      code,
      message: statusCode === 500 ? 'Internal server error' : err.message,
      ...(err.details ? { details: err.details } : {}),
    },
  });
}
