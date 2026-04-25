import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { renderHook, waitFor } from '@testing-library/react';
import { type ReactNode } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { tokens } from '@/lib/api';
import { VISITS_KEY, type Visit } from './useTodayBoard';
import { useReassignVisit } from './useReassignVisit';

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

function visit(overrides: Partial<Visit> = {}): Visit {
  return {
    id: 1,
    patient: 1,
    clinician: null,
    status: 'scheduled',
    required_skill: 'RN',
    window_start: '2026-04-24T08:00:00Z',
    window_end: '2026-04-24T10:00:00Z',
    ordering_seq: null,
    ...overrides,
  };
}

function mkWrapper(seedVisits: Visit[]) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  qc.setQueryData<Visit[]>(VISITS_KEY, seedVisits);
  function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  }
  return { qc, Wrapper };
}

describe('useReassignVisit', () => {
  beforeEach(() => {
    tokens.setAccess('A1');
    vi.restoreAllMocks();
  });
  afterEach(() => tokens.clear());

  it('happy path: optimistic patch is replaced by the server response', async () => {
    const seed = [visit({ id: 42 })];
    const updatedFromServer = visit({ id: 42, clinician: 17, status: 'assigned' });
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(jsonResponse(200, updatedFromServer));

    const { qc, Wrapper } = mkWrapper(seed);
    const { result } = renderHook(() => useReassignVisit(), { wrapper: Wrapper });
    result.current.mutate({ visitId: 42, clinicianId: 17 });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    const cache = qc.getQueryData<Visit[]>(VISITS_KEY)!;
    expect(cache[0].clinician).toBe(17);
    expect(cache[0].status).toBe('assigned');
  });

  it('409 rolls the cache back to the pre-mutation snapshot', async () => {
    const seed = [visit({ id: 42, clinician: null, status: 'scheduled' })];
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      jsonResponse(409, { detail: 'already assigned' }),
    );

    const { qc, Wrapper } = mkWrapper(seed);
    const { result } = renderHook(() => useReassignVisit(), { wrapper: Wrapper });
    result.current.mutate({ visitId: 42, clinicianId: 17 });
    await waitFor(() => expect(result.current.isError).toBe(true));
    const cache = qc.getQueryData<Visit[]>(VISITS_KEY)!;
    expect(cache[0].clinician).toBeNull();
    expect(cache[0].status).toBe('scheduled');
  });

  it('exposes the API error message to the caller', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      jsonResponse(409, { detail: 'visit already on_site' }),
    );
    const { Wrapper } = mkWrapper([visit({ id: 42 })]);
    const { result } = renderHook(() => useReassignVisit(), { wrapper: Wrapper });
    result.current.mutate({ visitId: 42, clinicianId: 17 });
    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error?.message).toBe('visit already on_site');
    expect(result.current.error?.status).toBe(409);
  });
});
