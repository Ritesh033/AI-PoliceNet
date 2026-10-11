import { describe, expect, it, vi } from 'vitest';
import { ApiClient, ApiError, normalizeBaseUrl } from './client';

const actor = { id: 'rev-demo', role: 'reviewer' as const };

function res(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json' } });
}

describe('normalizeBaseUrl', () => {
  it('accepts http and https addresses and strips trailing slashes', () => {
    expect(normalizeBaseUrl('http://localhost:8100/')).toBe('http://localhost:8100');
    expect(normalizeBaseUrl('  https://api.example.org/v1// ')).toBe('https://api.example.org/v1');
  });

  it('rejects anything else', () => {
    for (const bad of ['', 'localhost:8100', 'javascript:alert(1)', 'file:///etc/passwd', 'ftp://x']) {
      expect(normalizeBaseUrl(bad)).toBeNull();
    }
  });
});

describe('ApiClient', () => {
  it('sends the demo identity headers and returns parsed JSON', async () => {
    const fetchMock = vi.fn(async () => res(200, [{ id: 'APN-1001' }]));
    const client = new ApiClient('http://x', actor, fetchMock);
    const out = await client.listCases();
    expect(out).toEqual([{ id: 'APN-1001' }]);
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe('http://x/cases');
    expect(init.headers).toMatchObject({ 'X-Actor-Id': 'rev-demo', 'X-Actor-Role': 'reviewer' });
  });

  it('posts actions as JSON to the right case, escaping the id', async () => {
    const fetchMock = vi.fn(async () => res(200, { id: 'APN-1001' }));
    const client = new ApiClient('http://x', actor, fetchMock);
    await client.act('APN-1001/../x', { action: 'assign', note: 'n' });
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe('http://x/cases/APN-1001%2F..%2Fx/actions');
    expect(init.method).toBe('POST');
    expect(JSON.parse(init.body as string)).toEqual({ action: 'assign', note: 'n' });
    expect(init.headers).toMatchObject({ 'Content-Type': 'application/json' });
  });

  it('turns a policy refusal into an ApiError carrying the server code and message', async () => {
    const client = new ApiClient('http://x', actor, async () =>
      res(403, { error: 'role_not_permitted', detail: "Role 'reviewer' cannot perform 'register_fir'" }),
    );
    await expect(client.act('APN-1001', { action: 'register_fir', note: 'x' })).rejects.toMatchObject({
      status: 403,
      code: 'role_not_permitted',
      message: "Role 'reviewer' cannot perform 'register_fir'",
    });
  });

  it('handles framework-style errors and unreachable servers', async () => {
    const unauth = new ApiClient('http://x', actor, async () => res(401, { detail: 'headers required' }));
    await expect(unauth.health()).rejects.toMatchObject({ status: 401, code: 'http_401', message: 'headers required' });

    const down = new ApiClient('http://x', actor, async () => {
      throw new TypeError('Failed to fetch');
    });
    const err = await down.health().catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect((err as ApiError).code).toBe('network');
    expect((err as ApiError).message).toMatch(/APN_CORS_ORIGINS/);
  });
});
