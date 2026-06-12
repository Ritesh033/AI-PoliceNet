import rateLimit from 'express-rate-limit';
import { config } from '../config';

export const defaultRateLimiter = rateLimit({
  windowMs: config.rateLimit.default.windowMs,
  max: config.rateLimit.default.max,
  standardHeaders: true,
  legacyHeaders: false,
  message: { error: { code: 'RATE_LIMITED', message: 'Too many requests, please try again later' } },
});

export const authRateLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 20,
  standardHeaders: true,
  legacyHeaders: false,
  message: { error: { code: 'RATE_LIMITED', message: 'Too many auth attempts, please try again later' } },
});
