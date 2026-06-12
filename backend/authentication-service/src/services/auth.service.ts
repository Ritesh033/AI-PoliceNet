import bcrypt from 'bcryptjs';
import jwt from 'jsonwebtoken';
import crypto from 'crypto';
import { config } from '../config';
import { findUserByEmail, findUserByPhone, createUser, getUserRoles, User } from '../models/user';

interface TokenPair {
  accessToken: string;
  refreshToken: string;
  expiresIn: string;
}

function generateRegistrationId(userType: string, state: string = 'XX'): string {
  const prefix = userType === 'citizen' ? 'CIT' : 'GOV';
  const year = new Date().getFullYear();
  const seq = crypto.randomInt(100000, 999999);
  return `${prefix}-${state.toUpperCase()}-${year}-${seq}`;
}

function generateTokens(user: User, roles: string[]): TokenPair {
  const payload = {
    id: user.id,
    registrationId: user.registration_id,
    userType: user.user_type,
    roles,
  };

  const accessToken = jwt.sign(payload, config.jwt.secret, {
    expiresIn: config.jwt.accessExpiry,
  });

  const refreshToken = jwt.sign(
    { id: user.id, type: 'refresh' },
    config.jwt.secret,
    { expiresIn: config.jwt.refreshExpiry }
  );

  return { accessToken, refreshToken, expiresIn: config.jwt.accessExpiry };
}

export async function register(data: {
  email?: string;
  phone?: string;
  password: string;
  fullName: string;
  userType: string;
  state?: string;
  district?: string;
}): Promise<{ user: Omit<User, 'password_hash'>; tokens: TokenPair }> {
  if (data.email) {
    const existing = await findUserByEmail(data.email);
    if (existing) throw Object.assign(new Error('Email already registered'), { statusCode: 409, code: 'CONFLICT' });
  }

  if (data.phone) {
    const existing = await findUserByPhone(data.phone);
    if (existing) throw Object.assign(new Error('Phone already registered'), { statusCode: 409, code: 'CONFLICT' });
  }

  const passwordHash = await bcrypt.hash(data.password, config.bcrypt.saltRounds);
  const registrationId = generateRegistrationId(data.userType, data.state);

  const user = await createUser({
    registrationId,
    email: data.email,
    phone: data.phone,
    passwordHash,
    fullName: data.fullName,
    userType: data.userType,
    state: data.state,
    district: data.district,
  });

  const roles = await getUserRoles(user.id);
  const tokens = generateTokens(user, roles);

  const { password_hash: _, ...safeUser } = user;
  return { user: safeUser, tokens };
}

export async function login(data: {
  email?: string;
  phone?: string;
  password: string;
}): Promise<{ user: Omit<User, 'password_hash'>; tokens: TokenPair }> {
  let user: User | null = null;

  if (data.email) {
    user = await findUserByEmail(data.email);
  } else if (data.phone) {
    user = await findUserByPhone(data.phone);
  }

  if (!user) {
    throw Object.assign(new Error('Invalid credentials'), { statusCode: 401, code: 'UNAUTHORIZED' });
  }

  const isValid = await bcrypt.compare(data.password, user.password_hash);
  if (!isValid) {
    throw Object.assign(new Error('Invalid credentials'), { statusCode: 401, code: 'UNAUTHORIZED' });
  }

  if (!user.is_active) {
    throw Object.assign(new Error('Account deactivated'), { statusCode: 403, code: 'FORBIDDEN' });
  }

  const roles = await getUserRoles(user.id);
  const tokens = generateTokens(user, roles);

  const { password_hash: _, ...safeUser } = user;
  return { user: safeUser, tokens };
}

export async function refreshAccessToken(refreshToken: string): Promise<TokenPair> {
  try {
    const payload = jwt.verify(refreshToken, config.jwt.secret) as { id: string; type: string };
    if (payload.type !== 'refresh') {
      throw new Error('Invalid token type');
    }

    const { findUserById } = await import('../models/user');
    const user = await findUserById(payload.id);
    if (!user || !user.is_active) {
      throw new Error('User not found or inactive');
    }

    const roles = await getUserRoles(user.id);
    return generateTokens(user, roles);
  } catch {
    throw Object.assign(new Error('Invalid refresh token'), { statusCode: 401, code: 'UNAUTHORIZED' });
  }
}

export async function generateOTP(): Promise<string> {
  return crypto.randomInt(100000, 999999).toString();
}
