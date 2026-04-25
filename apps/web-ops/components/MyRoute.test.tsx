import { I18nProvider } from '@heroui/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

// Stub the realtime client out — its background ws-token mint would steal
// our mocked fetch responses, and the dispatcher logic is tested separately
// in useMyRoute.test.ts.
vi.mock('@/hooks/useRealtimeEvents', () => ({
  useRealtimeEvents: () => {},
  RtClient: class {},
}));

import { tokens } from '@/lib/api';
import { MY_VISITS_KEY } from '@/hooks/useMyRoute';
import type { Visit } from '@/hooks/useTodayBoard';
import { MyRoute } from './MyRoute';

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

const VISITS: Visit[] = [
  {
    id: 1, patient: 1, clinician: 7, status: 'assigned', required_skill: 'RN',
    window_start: '2026-04-24T08:00:00Z', window_end: '2026-04-24T10:00:00Z', ordering_seq: 0,
  },
  {
    id: 2, patient: 2, clinician: 7, status: 'on_site', required_skill: 'RN',
    window_start: '2026-04-24T09:00:00Z', window_end: '2026-04-24T11:00:00Z', ordering_seq: 1,
  },
];

function renderRoute(seedVisits: Visit[] = VISITS) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: Infinity } },
  });
  qc.setQueryData<Visit[]>(MY_VISITS_KEY, seedVisits);
  return render(
    <I18nProvider locale="en-US">
      <QueryClientProvider client={qc}>
        <MyRoute clinicianId={7} tenantId={1} />
      </QueryClientProvider>
    </I18nProvider>,
  );
}

describe('<MyRoute />', () => {
  beforeEach(() => {
    tokens.setAccess('A1');
  });
  afterEach(() => {
    vi.restoreAllMocks();
    tokens.clear();
  });

  it('renders one card per visit in ordering_seq order', () => {
    renderRoute();
    const list = screen.getByTestId('my-route');
    expect(list.children.length).toBe(2);
    expect(list.children[0]).toHaveAttribute('data-testid', 'my-visit-1');
  });

  it('Check In on an assigned visit POSTs check-in and flips status', async () => {
    const updated = { ...VISITS[0], status: 'on_site' };
    const fetchSpy = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(jsonResponse(200, updated));
    renderRoute();
    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: /check in visit 1/i }));
    await waitFor(() => {
      const [url] = fetchSpy.mock.calls[0]!;
      expect(String(url)).toContain('/api/v1/visits/1/check-in/');
    });
  });

  it('Check Out shows for on_site visits', () => {
    renderRoute();
    expect(screen.getByRole('button', { name: /check out visit 2/i })).toBeInTheDocument();
  });

  it('409 reverts the optimistic patch and renders the error', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      jsonResponse(409, { detail: 'wrong status' }),
    );
    renderRoute();
    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: /check in visit 1/i }));
    expect(await screen.findByRole('alert')).toHaveTextContent(/wrong status/i);
  });

  it('renders the empty state when there are no visits', () => {
    renderRoute([]);
    expect(screen.getByText(/no visits assigned today/i)).toBeInTheDocument();
  });
});
