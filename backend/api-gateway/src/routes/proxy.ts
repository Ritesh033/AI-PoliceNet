import { Router } from 'express';
import { createProxyMiddleware, Options } from 'http-proxy-middleware';
import { config } from '../config';
import { authenticate } from '../middleware/auth';
import { authRateLimiter } from '../middleware/rate-limiter';

const router = Router();

function proxy(target: string, pathRewrite?: Record<string, string>): ReturnType<typeof createProxyMiddleware> {
  const options: Options = {
    target,
    changeOrigin: true,
    pathRewrite,
    on: {
      error: (err, _req, res) => {
        if ('writeHead' in res) {
          (res as any).status(503).json({
            error: { code: 'SERVICE_UNAVAILABLE', message: 'Downstream service unavailable' },
          });
        }
      },
    },
  };
  return createProxyMiddleware(options);
}

// Public routes (no auth required)
router.use('/v1/auth', authRateLimiter, proxy(config.services.auth, { '^/v1/auth': '/auth' }));

// Protected routes
router.use('/v1/citizens', authenticate, proxy(config.services.citizen, { '^/v1/citizens': '/citizens' }));
router.use('/v1/fir', authenticate, proxy(config.services.fir, { '^/v1/fir': '/fir' }));
router.use('/v1/evidence', authenticate, proxy(config.services.evidence, { '^/v1/evidence': '/evidence' }));
router.use('/v1/social-media', authenticate, proxy(config.services.socialMedia, { '^/v1/social-media': '/social-media' }));
router.use('/v1/accountability', authenticate, proxy(config.services.accountability, { '^/v1/accountability': '/accountability' }));
router.use('/v1/notifications', authenticate, proxy(config.services.notification, { '^/v1/notifications': '/notifications' }));
router.use('/v1/investigations', authenticate, proxy(config.services.investigation, { '^/v1/investigations': '/investigations' }));
router.use('/v1/court', authenticate, proxy(config.services.court, { '^/v1/court': '/court' }));
router.use('/v1/analytics', authenticate, proxy(config.services.analytics, { '^/v1/analytics': '/analytics' }));
router.use('/v1/audit', authenticate, proxy(config.services.audit, { '^/v1/audit': '/audit' }));
router.use('/v1/ai', authenticate, proxy(config.services.ai, { '^/v1/ai': '/ai' }));

export default router;
