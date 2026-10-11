import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { LiveCases } from './LiveCases';
import type { ApiCase } from '../../api/types';

const NOW = Date.UTC(2026, 9, 10, 12, 0);

function makeCase(over: Partial<ApiCase>): ApiCase {
  return {
    id: 'APN-1001', kind: 'social', category: 'threat', title: 'Reported threat in a public video',
    summary: 'Spoken statements appear to threaten violence.', priority: 'urgent', confidence: 0.87, stage: 'received',
    behaviors: ['threat'], situation: [], content_fingerprint: 'fp-demo-0001', checks: [], referred_to_role: null,
    notice_served_at: null, window_closes_at: null, response_received: false, court_reviewed: false, appeal_open: false,
    decision_due_at: new Date(NOW + 3 * 3600_000).toISOString(), sla_breached: false, linked_to: null,
    dismissal_recommended: false, fresh_registration_permitted: false,
    context_missing: ['cross_platform_copies', 'edit_detection', 'full_context', 'media_source'],
    context_findings_undermining_flag: 0, created_at: new Date(NOW - 3600_000).toISOString(),
    updated_at: new Date(NOW - 3600_000).toISOString(), ai_notice: 'AI output is advisory. Registration, referral and closure are human decisions.',
    items: [{
      id: 1, kind: 'evidence', label: 'video (sample)', outcome: null, description: '', sha256: 'ab'.repeat(32),
      preview_withheld: true, late: false, added_by: 'model-v1', added_at: new Date(NOW).toISOString(),
    }],
    ...over,
  };
}

const META = {
  checks: ['authenticity', 'context', 'wellbeing'],
  actions: {
    assign: { roles: ['reviewer'], from_stages: ['received'], to_stage: 'in_review', note_required: false, params: [] },
    no_action: { roles: ['reviewer'], from_stages: ['received', 'in_review'], to_stage: 'closed_no_action', note_required: true, params: [] },
    record_check: { roles: ['reviewer'], from_stages: ['received', 'in_review'], to_stage: null, note_required: false, params: ['check'] },
    court_close: { roles: ['judicial_authority'], from_stages: ['fir_registered'], to_stage: 'closed_by_court', note_required: true, params: [] },
    appeal: { roles: ['citizen'], from_stages: ['fir_registered'], to_stage: null, note_required: true, params: [] },
  },
};

type Handler = (req: { url: string; method: string; headers: Record<string, string>; body: unknown }) => { status: number; body: unknown };

function installFetch(handler: Handler) {
  const calls: Array<{ url: string; method: string; headers: Record<string, string>; body: unknown }> = [];
  vi.stubGlobal('fetch', vi.fn(async (url: string, init: RequestInit = {}) => {
    const req = {
      url: url.replace('http://localhost:8100', ''), method: init.method ?? 'GET',
      headers: init.headers as Record<string, string>, body: init.body ? JSON.parse(init.body as string) : null,
    };
    calls.push(req);
    const out = handler(req);
    return new Response(JSON.stringify(out.body), { status: out.status, headers: { 'content-type': 'application/json' } });
  }));
  return calls;
}

beforeEach(() => vi.useRealTimers());
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe('LiveCases', () => {
  it('connects, lists cases and shows the full-context checklist and hash-only evidence', async () => {
    installFetch(({ url }) => {
      if (url === '/health') return { status: 200, body: { status: 'ok', auth: 'demo-stub' } };
      if (url === '/meta/actions') return { status: 200, body: META };
      if (url === '/cases') return { status: 200, body: [makeCase({})] };
      return { status: 404, body: {} };
    });
    const user = userEvent.setup();
    render(<LiveCases now={NOW} />);
    const connection = screen.getByRole('region', { name: 'Case core (live API)' });
    expect(within(connection).getByRole('status')).toHaveTextContent('Not connected');
    await user.click(screen.getByRole('button', { name: 'Connect' }));

    await waitFor(() =>
      expect(within(connection).getByRole('status')).toHaveTextContent(/Connected to http:\/\/localhost:8100 as Reviewer/),
    );
    expect(screen.getByRole('button', { name: 'APN-1001' })).toBeInTheDocument();
    const detail = screen.getByRole('region', { name: /APN-1001/ });
    expect(within(detail).getAllByText(/not yet researched/i)).toHaveLength(4);
    expect(within(detail).getByText(/human acknowledgement/i)).toBeInTheDocument();
    expect(within(detail).getByText(/preview withheld/i)).toBeInTheDocument();
    expect(within(detail).getByText('ab'.repeat(32))).toBeInTheDocument();
    expect(detail).toHaveTextContent(/AI output is advisory/);
    // Citizen-only actions are never offered in the console.
    expect(within(detail).queryByRole('button', { name: /appeal/i })).not.toBeInTheDocument();
  });

  it('shows the server refusal verbatim and records a successful action after a reason is given', async () => {
    const calls = installFetch(({ url, method, body }) => {
      if (url === '/health') return { status: 200, body: { status: 'ok', auth: 'demo-stub' } };
      if (url === '/meta/actions') return { status: 200, body: META };
      if (url === '/cases') return { status: 200, body: [makeCase({})] };
      if (url === '/cases/APN-1001/actions' && method === 'POST') {
        const b = body as { note?: string };
        if (!b.note) return { status: 422, body: { error: 'note_required', detail: "'no_action' needs a written reason, recorded in the audit trail" } };
        return { status: 200, body: makeCase({ stage: 'closed_no_action' }) };
      }
      return { status: 404, body: {} };
    });
    const user = userEvent.setup();
    render(<LiveCases now={NOW} />);
    await user.click(screen.getByRole('button', { name: 'Connect' }));
    const detail = await screen.findByRole('region', { name: /APN-1001/ });

    await user.click(within(detail).getByRole('button', { name: 'No action' }));
    await user.click(within(detail).getByRole('button', { name: /submit: no action/i }));
    const alert = await within(detail).findByRole('alert');
    expect(alert).toHaveTextContent(/refused by the server/i);
    expect(alert).toHaveTextContent(/needs a written reason/i);
    expect(alert).toHaveTextContent('note_required');

    await user.type(within(detail).getByLabelText(/written reason/i), 'Scene from a TV drama');
    await user.click(within(detail).getByRole('button', { name: /submit: no action/i }));
    await waitFor(() => expect(within(detail).getByRole('status')).toHaveTextContent(/no action: recorded in the ledger/i));
    const post = calls.filter((c) => c.method === 'POST').at(-1)!;
    expect(post.body).toEqual({ action: 'no_action', note: 'Scene from a TV drama' });
    expect(post.headers).toMatchObject({ 'X-Actor-Id': 'rev-demo', 'X-Actor-Role': 'reviewer' });
    expect(calls.filter((c) => c.url === '/cases').length).toBeGreaterThanOrEqual(2); // refreshed after the action
  });

  it('lets a judicial authority read and verify the ledger, while a reviewer is told it cannot', async () => {
    const fir = makeCase({ id: 'APN-1007', stage: 'fir_registered', dismissal_recommended: true });
    const calls = installFetch(({ url, headers }) => {
      if (url === '/health') return { status: 200, body: { status: 'ok', auth: 'demo-stub' } };
      if (url === '/meta/actions') return { status: 200, body: META };
      if (url === '/cases') return { status: 200, body: [fir] };
      if (url.startsWith('/ledger') && !['auditor', 'judicial_authority'].includes(headers['X-Actor-Role'])) {
        return { status: 403, body: { error: 'forbidden', detail: 'Ledger access is for auditors and judicial authorities' } };
      }
      if (url.startsWith('/ledger/verify')) {
        return { status: 200, body: { chain_valid: true, entries_checked: 12, first_bad_seq: null, reason: null, projection_consistent: true, projection_problems: [] } };
      }
      if (url.startsWith('/ledger')) {
        return { status: 200, body: [{ seq: 1, ts: new Date(NOW).toISOString(), case_id: 'APN-1007', actor_id: 'model-v1', actor_role: 'ai_service', actor_kind: 'ai', action: 'case.created', payload: {}, hash: 'h' }] };
      }
      return { status: 404, body: {} };
    });
    const user = userEvent.setup();
    render(<LiveCases now={NOW} />);
    await user.click(screen.getByRole('button', { name: 'Connect' }));
    const detail = await screen.findByRole('region', { name: /APN-1007/ });
    expect(detail).toHaveTextContent(/AI recommends dismissal \(court decides\)/);
    expect(detail).toHaveTextContent(/readable by auditors and judicial authorities/);

    await user.selectOptions(screen.getByLabelText('Act as'), 'judicial_authority');
    const judicial = await screen.findByRole('region', { name: /APN-1007/ });
    await waitFor(() => expect(within(judicial).getByText(/case\.created/)).toBeInTheDocument());
    // The new role must never be paired with the previous role's identity while the switch is in flight.
    expect(within(judicial).queryByRole('alert')).not.toBeInTheDocument();
    expect(calls.filter((c) => c.url.startsWith('/ledger') && c.headers['X-Actor-Role'] === 'reviewer')).toHaveLength(0);
    await user.click(within(judicial).getByRole('button', { name: /verify ledger integrity/i }));
    expect(await within(judicial).findByText(/chain valid: 12 entries checked/i)).toBeInTheDocument();
    expect(within(judicial).getByRole('button', { name: 'Court: close FIR' })).toBeInTheDocument();
  });

  it('explains a connection failure and how to start the API', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => { throw new TypeError('Failed to fetch'); }));
    const user = userEvent.setup();
    render(<LiveCases now={NOW} />);
    await user.click(screen.getByRole('button', { name: 'Connect' }));
    expect(await screen.findByRole('alert')).toHaveTextContent(/could not reach the case-core api/i);
    expect(screen.getByText(/python -m app\.demo_seed/)).toBeInTheDocument();
  });

  it('rejects a non-http address without making a request', async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
    const user = userEvent.setup();
    render(<LiveCases now={NOW} />);
    const input = screen.getByLabelText('API address');
    await user.clear(input);
    await user.type(input, 'javascript:alert(1)');
    await user.click(screen.getByRole('button', { name: 'Connect' }));
    expect(screen.getByRole('alert')).toHaveTextContent(/valid http/i);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
