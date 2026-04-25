import { I18nProvider } from '@heroui/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { tokens } from '@/lib/api';
import { VISITS_KEY, type Clinician, type Visit } from '@/hooks/useTodayBoard';
import { ReassignModal } from './ReassignModal';

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

const VISIT: Visit = {
  id: 42,
  patient: 1,
  clinician: null,
  status: 'scheduled',
  required_skill: 'LVN',
  window_start: '2026-04-24T08:00:00Z',
  window_end: '2026-04-24T10:00:00Z',
  ordering_seq: null,
};

const CLINICIANS: Clinician[] = [
  { id: 1, user: 1, credential: 'RN', home_lat: 0, home_lon: 0 },
  { id: 2, user: 2, credential: 'LVN', home_lat: 0, home_lon: 0 },
  { id: 3, user: 3, credential: 'MA', home_lat: 0, home_lon: 0 },
  { id: 4, user: 4, credential: 'phlebotomist', home_lat: 0, home_lon: 0 },
];

function renderModal(onClose: () => void = vi.fn()) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  qc.setQueryData<Visit[]>(VISITS_KEY, [VISIT]);
  return render(
    <I18nProvider locale="en-US">
      <QueryClientProvider client={qc}>
        <ReassignModal visit={VISIT} clinicians={CLINICIANS} open onClose={onClose} />
      </QueryClientProvider>
    </I18nProvider>,
  );
}

describe('<ReassignModal />', () => {
  beforeEach(() => {
    tokens.setAccess('A1');
    vi.restoreAllMocks();
  });
  afterEach(() => tokens.clear());

  it('lists only credentialed clinicians (RN + LVN for an LVN visit)', () => {
    renderModal();
    const list = screen.getByTestId('clinician-list');
    expect(list.children.length).toBe(2);
    expect(list.textContent).toContain('Clinician #1');
    expect(list.textContent).toContain('Clinician #2');
    expect(list.textContent).not.toContain('Clinician #3');
    expect(list.textContent).not.toContain('Clinician #4');
  });

  it('clicking a row POSTs assign with the matching clinician_id', async () => {
    const updated = { ...VISIT, clinician: 2, status: 'assigned' };
    const fetchSpy = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(jsonResponse(200, updated));
    const onClose = vi.fn();
    renderModal(onClose);
    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: /assign to 2/i }));
    await waitFor(() => expect(onClose).toHaveBeenCalled());
    const [url, init] = fetchSpy.mock.calls[0]!;
    expect(String(url)).toContain('/api/v1/visits/42/assign/');
    expect(init?.method).toBe('POST');
    const body = JSON.parse((init as RequestInit).body as string);
    expect(body.clinician_id).toBe(2);
  });

  it('409 keeps the modal open and renders the error message', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      jsonResponse(409, { detail: 'visit already advanced' }),
    );
    const onClose = vi.fn();
    renderModal(onClose);
    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: /assign to 1/i }));
    expect(await screen.findByRole('alert')).toHaveTextContent(/already advanced/i);
    expect(onClose).not.toHaveBeenCalled();
  });
});
