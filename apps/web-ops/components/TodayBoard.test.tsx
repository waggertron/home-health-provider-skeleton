import { I18nProvider } from '@heroui/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { tokens } from '@/lib/api';
import type { Visit, Clinician } from '@/hooks/useTodayBoard';
import { TodayBoard } from './TodayBoard';

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

const VISITS: Visit[] = [
  {
    id: 1, patient: 1, clinician: null, status: 'scheduled', required_skill: 'RN',
    window_start: '2026-04-24T08:00:00Z', window_end: '2026-04-24T10:00:00Z',
    ordering_seq: null,
  },
  {
    id: 2, patient: 2, clinician: 7, status: 'assigned', required_skill: 'MA',
    window_start: '2026-04-24T09:00:00Z', window_end: '2026-04-24T11:00:00Z',
    ordering_seq: 0,
  },
  {
    id: 3, patient: 3, clinician: 7, status: 'completed', required_skill: 'RN',
    window_start: '2026-04-24T07:00:00Z', window_end: '2026-04-24T09:00:00Z',
    ordering_seq: null,
  },
];

const CLINICIANS: Clinician[] = [
  { id: 7, user: 1, credential: 'RN', home_lat: 34.0, home_lon: -118.0 },
];

function setupFetch() {
  const calls: string[] = [];
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
    const url = typeof input === 'string' ? input : (input as Request).url;
    calls.push(url);
    if (url.includes('/visits/')) return jsonResponse(200, VISITS);
    if (url.includes('/clinicians/')) return jsonResponse(200, CLINICIANS);
    if (url.includes('/optimize')) {
      return jsonResponse(202, { job_id: 'JOB-1', status: 'PENDING' });
    }
    return jsonResponse(404, {});
  });
  return calls;
}

function renderBoard() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <I18nProvider locale="en-US">
      <QueryClientProvider client={qc}>
        <TodayBoard tenantId={1} />
      </QueryClientProvider>
    </I18nProvider>,
  );
}

describe('<TodayBoard />', () => {
  beforeEach(() => {
    tokens.setAccess('A1');
    vi.restoreAllMocks();
  });
  afterEach(() => tokens.clear());

  it('renders one card per visit on first load', async () => {
    setupFetch();
    renderBoard();
    await waitFor(() =>
      expect(screen.getByTestId('visit-grid').children.length).toBe(VISITS.length),
    );
    expect(screen.getByText(/3 of 3 visits/)).toBeInTheDocument();
  });

  it('status filter narrows the grid to matching cards', async () => {
    setupFetch();
    renderBoard();
    const user = userEvent.setup();
    await waitFor(() => screen.getByTestId('visit-grid'));
    await user.selectOptions(screen.getByLabelText(/status/i), 'completed');
    await waitFor(() =>
      expect(screen.getByTestId('visit-grid').children.length).toBe(1),
    );
    expect(screen.getByText(/1 of 3 visits/)).toBeInTheDocument();
  });

  it('Optimize Day button POSTs /schedule/<today>/optimize', async () => {
    const calls = setupFetch();
    renderBoard();
    const user = userEvent.setup();
    await waitFor(() => screen.getByRole('button', { name: /optimize/i }));
    await user.click(screen.getByRole('button', { name: /optimize/i }));
    await waitFor(() => expect(calls.some((u) => u.includes('/optimize'))).toBe(true));
  });
});
