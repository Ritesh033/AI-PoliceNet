import { Router, Request, Response, NextFunction } from 'express';
import { z } from 'zod';
import * as authService from '../services/auth.service';

const router = Router();

const registerSchema = z.object({
  email: z.string().email().optional(),
  phone: z.string().min(10).max(15).optional(),
  password: z.string().min(8).max(128),
  fullName: z.string().min(2).max(255),
  userType: z.enum(['citizen', 'officer', 'inspector', 'admin', 'judge', 'moderator']),
  state: z.string().optional(),
  district: z.string().optional(),
}).refine((data) => data.email || data.phone, {
  message: 'Either email or phone is required',
});

const loginSchema = z.object({
  email: z.string().email().optional(),
  phone: z.string().optional(),
  password: z.string(),
}).refine((data) => data.email || data.phone, {
  message: 'Either email or phone is required',
});

const refreshSchema = z.object({
  refreshToken: z.string(),
});

router.post('/auth/register', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const data = registerSchema.parse(req.body);
    const result = await authService.register(data);
    res.status(201).json({
      message: 'Registration successful',
      data: result,
    });
  } catch (error) {
    next(error);
  }
});

router.post('/auth/login', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const data = loginSchema.parse(req.body);
    const result = await authService.login(data);
    res.json({
      message: 'Login successful',
      data: result,
    });
  } catch (error) {
    next(error);
  }
});

router.post('/auth/refresh', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const { refreshToken } = refreshSchema.parse(req.body);
    const tokens = await authService.refreshAccessToken(refreshToken);
    res.json({
      message: 'Token refreshed',
      data: tokens,
    });
  } catch (error) {
    next(error);
  }
});

router.post('/auth/otp/send', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const { phone, email } = req.body;
    const otp = await authService.generateOTP();
    // TODO: Store OTP in Redis and send via notification service
    res.json({
      message: 'OTP sent successfully',
      data: { expiresIn: '5 minutes' },
    });
  } catch (error) {
    next(error);
  }
});

router.post('/auth/logout', (req: Request, res: Response) => {
  // TODO: Invalidate refresh token in Redis
  res.json({ message: 'Logged out successfully' });
});

export default router;
