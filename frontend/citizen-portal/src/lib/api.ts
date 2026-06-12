const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080/v1';

interface ApiOptions {
  method?: string;
  body?: unknown;
  token?: string;
}

export async function api<T>(endpoint: string, options: ApiOptions = {}): Promise<T> {
  const { method = 'GET', body, token } = options;

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_URL}${endpoint}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ error: { message: 'Request failed' } }));
    throw new Error(error.error?.message || `HTTP ${res.status}`);
  }

  return res.json();
}

export const authApi = {
  login: (data: { email?: string; phone?: string; password: string }) =>
    api('/auth/login', { method: 'POST', body: data }),
  register: (data: Record<string, unknown>) =>
    api('/auth/register', { method: 'POST', body: data }),
  refresh: (refreshToken: string) =>
    api('/auth/refresh', { method: 'POST', body: { refreshToken } }),
};

export const citizenApi = {
  getProfile: (token: string) =>
    api('/citizens/profile', { token }),
  updateProfile: (data: Record<string, unknown>, token: string) =>
    api('/citizens/profile', { method: 'PUT', body: data, token }),
  fileComplaint: (data: Record<string, unknown>, token: string) =>
    api('/citizens/complaints', { method: 'POST', body: data, token }),
  getComplaints: (token: string, page = 1) =>
    api(`/citizens/complaints?page=${page}`, { token }),
};

export const firApi = {
  getById: (id: string, token: string) =>
    api(`/fir/${id}`, { token }),
  list: (token: string, params: Record<string, string> = {}) => {
    const qs = new URLSearchParams(params).toString();
    return api(`/fir?${qs}`, { token });
  },
  getAuditTrail: (id: string, token: string) =>
    api(`/fir/${id}/audit`, { token }),
};

export const evidenceApi = {
  upload: (data: Record<string, unknown>, token: string) =>
    api('/evidence/upload', { method: 'POST', body: data, token }),
  getById: (id: string, token: string) =>
    api(`/evidence/${id}`, { token }),
  getChainOfCustody: (id: string, token: string) =>
    api(`/evidence/${id}/chain-of-custody`, { token }),
};
