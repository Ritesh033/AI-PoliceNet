export const config = {
  port: parseInt(process.env.AUTH_PORT || '8001', 10),
  nodeEnv: process.env.NODE_ENV || 'development',
  jwt: {
    secret: process.env.JWT_SECRET || 'dev-secret-change-in-production',
    accessExpiry: process.env.JWT_ACCESS_EXPIRY || '15m',
    refreshExpiry: process.env.JWT_REFRESH_EXPIRY || '7d',
  },
  postgres: {
    host: process.env.POSTGRES_HOST || 'localhost',
    port: parseInt(process.env.POSTGRES_PORT || '5432', 10),
    database: process.env.POSTGRES_DB || 'ai_policenet',
    user: process.env.POSTGRES_USER || 'policenet_admin',
    password: process.env.POSTGRES_PASSWORD || 'changeme',
  },
  redis: {
    host: process.env.REDIS_HOST || 'localhost',
    port: parseInt(process.env.REDIS_PORT || '6379', 10),
    password: process.env.REDIS_PASSWORD,
  },
  otp: {
    expiryMinutes: parseInt(process.env.OTP_EXPIRY_MINUTES || '5', 10),
    length: 6,
  },
  mfa: {
    issuer: process.env.MFA_ISSUER || 'AI-PoliceNet',
  },
  bcrypt: {
    saltRounds: 12,
  },
  session: {
    maxFailedAttempts: 5,
    lockoutMinutes: 30,
  },
};
