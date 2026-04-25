import { I18nProvider } from '@heroui/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { tokens } from '@/lib/api';
import { POSITIONS_KEY, type ClinicianPosition } from '@/hooks/useClinicianPositions';
import { OpsMap } from './OpsMap';

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

const POSITIONS: ClinicianPosition[] = [
  { clinician: 1, lat: 34.0, lon: -118.0, ts: 'T' },
  { clinician: 2, lat: 34.1, lon: -118.2, ts: 'T' },
];

function renderMap(seed: ClinicianPosition[] | null = null) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  if (seed) qc.setQueryData(POSITIONS_KEY, seed);
  return render(
    <I18nProvider locale="en-US">
      <QueryClientProvider client={qc}>
        <OpsMap tenantId={1} />
      </QueryClientProvider>
    </I18nProvider>,
  );
}

describe('<OpsMap />', () => {
  beforeEach(() => {
    tokens.setAccess('A1');
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(jsonResponse(200, POSITIONS));
  });
  afterEach(() => {
    vi.restoreAllMocks();
    tokens.clear();
  });

  it('renders an svg map shell', () => {
    renderMap(POSITIONS);
    expect(screen.getByTestId('ops-map')).toBeInTheDocument();
  });

  it('places one marker per seeded clinician position', async () => {
    renderMap(POSITIONS);
    expect(screen.getByTestId('clinician-marker-1')).toBeInTheDocument();
    expect(screen.getByTestId('clinician-marker-2')).toBeInTheDocument();
    expect(screen.getByText(/2 clinicians on the map/)).toBeInTheDocument();
  });

  it('fetches /positions/latest/ on first mount when cache is empty', async () => {
    renderMap();
    await waitFor(() => expect(screen.getByTestId('clinician-marker-1')).toBeInTheDocument());
  });
});
