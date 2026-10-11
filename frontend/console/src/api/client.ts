import type { ActionMeta, ActionRequest, ApiCase, ApiRole, LedgerRow, VerifyResult } from './types';

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export interface ApiActor {
  id: string;
  role: ApiRole;
}

/** Accepts only http(s) URLs and strips a trailing slash. Returns null when the input is not usable. */
export function normalizeBaseUrl(raw: string): string | null {
  try {
    const url = new URL(raw.trim());
    if (url.protocol !== 'http:' && url.protocol !== 'https:') return null;
    return `${url.origin}${url.pathname.replace(/\/+$/, '')}`;
  } catch {
    return null;
  }
}

type FetchLike = (input: string, init?: RequestInit) => Promise<Response>;

/** Thin typed client for the case-core API. Identity is the demo header stub; the server enforces every rule. */
export class ApiClient {
  constructor(
    private baseUrl: string,
    public readonly actor: ApiActor,
    private fetchImpl: FetchLike = (input, init) => fetch(input, init),
  ) {}

  private async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    let res: Response;
    try {
      res = await this.fetchImpl(`${this.baseUrl}${path}`, {
        ...init,
        headers: {
          'X-Actor-Id': this.actor.id,
          'X-Actor-Role': this.actor.role,
          ...(init.body ? { 'Content-Type': 'application/json' } : {}),
        },
      });
    } catch {
      throw new ApiError(0, 'network', `Could not reach the case-core API at ${this.baseUrl}. Is it running, and is this origin allowed by APN_CORS_ORIGINS?`);
    }
    const body: unknown = await res.json().catch(() => null);
    if (!res.ok) {
      const b = (body ?? {}) as { error?: string; detail?: unknown };
      const detail = typeof b.detail === 'string' ? b.detail : `HTTP ${res.status}`;
      throw new ApiError(res.status, b.error ?? `http_${res.status}`, detail);
    }
    return body as T;
  }

  health() {
    return this.request<{ status: string; auth: string }>('/health');
  }

  metaActions() {
    return this.request<ActionMeta>('/meta/actions');
  }

  listCases() {
    return this.request<ApiCase[]>('/cases');
  }

  act(caseId: string, body: ActionRequest) {
    return this.request<ApiCase>(`/cases/${encodeURIComponent(caseId)}/actions`, {
      method: 'POST',
      body: JSON.stringify(body),
    });
  }

  ledger(caseId: string) {
    return this.request<LedgerRow[]>(`/ledger?case_id=${encodeURIComponent(caseId)}&limit=200`);
  }

  verify() {
    return this.request<VerifyResult>('/ledger/verify');
  }
}
