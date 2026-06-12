import { Pool } from 'pg';
import { config } from '../config';

export const pool = new Pool({
  host: config.postgres.host,
  port: config.postgres.port,
  database: config.postgres.database,
  user: config.postgres.user,
  password: config.postgres.password,
  max: 20,
  idleTimeoutMillis: 30_000,
});

export interface User {
  id: string;
  registration_id: string;
  email: string | null;
  phone: string | null;
  password_hash: string;
  full_name: string;
  date_of_birth: string | null;
  address: string | null;
  state: string | null;
  district: string | null;
  user_type: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: Date;
  updated_at: Date;
}

export interface Session {
  id: string;
  user_id: string;
  refresh_token: string;
  ip_address: string;
  user_agent: string;
  expires_at: Date;
  created_at: Date;
}

export async function findUserByEmail(email: string): Promise<User | null> {
  const result = await pool.query('SELECT * FROM users WHERE email = $1 AND is_active = true', [email]);
  return result.rows[0] || null;
}

export async function findUserByPhone(phone: string): Promise<User | null> {
  const result = await pool.query('SELECT * FROM users WHERE phone = $1 AND is_active = true', [phone]);
  return result.rows[0] || null;
}

export async function findUserById(id: string): Promise<User | null> {
  const result = await pool.query('SELECT * FROM users WHERE id = $1', [id]);
  return result.rows[0] || null;
}

export async function createUser(data: {
  registrationId: string;
  email?: string;
  phone?: string;
  passwordHash: string;
  fullName: string;
  userType: string;
  state?: string;
  district?: string;
}): Promise<User> {
  const result = await pool.query(
    `INSERT INTO users (registration_id, email, phone, password_hash, full_name, user_type, state, district)
     VALUES ($1, $2, $3, $4, $5, $6, $7, $8) RETURNING *`,
    [data.registrationId, data.email, data.phone, data.passwordHash, data.fullName, data.userType, data.state, data.district]
  );
  return result.rows[0];
}

export async function getUserRoles(userId: string): Promise<string[]> {
  const result = await pool.query(
    'SELECT r.name FROM roles r JOIN user_roles ur ON r.id = ur.role_id WHERE ur.user_id = $1',
    [userId]
  );
  return result.rows.map((row: { name: string }) => row.name);
}
