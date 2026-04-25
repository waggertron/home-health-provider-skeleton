import { I18nProvider } from '@heroui/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { tokens } from '@/lib/api';
import { PositionPinger } from './PositionPinger';

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

function renderPinger() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <I18nProvider locale="en-US">
      <QueryClientProvider client={qc}>
        <PositionPinger />
      </QueryClientProvider>
    </I18nProvider>,
  );
}

describe('<PositionPinger />', () => {
  beforeEach(() => {
    tokens.setAccess('A1');
  });
  afterEach(() => {
    vi.restoreAllMocks();
    tokens.clear();
  });

  it('POSTs /api/v1/positions/ with {lat, lon, ts} on click', async () => {
    const fetchSpy = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(jsonResponse(201, { id: 1 }));
    renderPinger();
    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: /send gps/i }));
    await waitFor(() => expect(fetchSpy).toHaveBeenCalled());
    const [url, init] = fetchSpy.mock.calls[0]!;
    expect(String(url)).toContain('/api/v1/positions/');
    const body = JSON.parse((init as RequestInit).body as string);
    expect(typeof body.lat).toBe('number');
    expect(typeof body.lon).toBe('number');
    expect(typeof body.ts).toBe('string');
  });

  it('shows the most-recent coords after a successful send', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(jsonResponse(201, { id: 1 }));
    renderPinger();
    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: /send gps/i }));
    expect(await screen.findByTestId('last-ping')).toBeInTheDocument();
  });

  it('renders an error from the API', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      jsonResponse(403, { detail: 'not a clinician' }),
    );
    renderPinger();
    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: /send gps/i }));
    expect(await screen.findByRole('alert')).toHaveTextContent(/not a clinician/i);
  });
});
