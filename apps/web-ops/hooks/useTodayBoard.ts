'use client';

import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useCallback } from 'react';
import { apiFetch } from '@/lib/api';
import type { RtEvent } from './useRealtimeEvents';
import { useRealtimeEvents } from './useRealtimeEvents';

export interface Visit {
  id: number;
  patient: number;
  clinician: number | null;
  status: string;
  required_skill: string;
  window_start: string;
  window_end: string;
  ordering_seq: number | null;
}

export interface Clinician {
  id: number;
  user: number;
  credential: string;
  home_lat: number;
  home_lon: number;
}

export const VISITS_KEY = ['visits', 'today'] as const;
export const CLINICIANS_KEY = ['clinicians'] as const;

async function fetchList<T>(path: string): Promise<T[]> {
  const r = await apiFetch(path);
  if (!r.ok) throw new Error(`${path}: ${r.status}`);
  const data = (await r.json()) as T[] | { results: T[] };
  return Array.isArray(data) ? data : data.results;
}

export interface DispatcherOps {
  setVisits(updater: (current: Visit[] | undefined) => Visit[] | undefined): void;
  invalidateVisits(): void;
}

/**
 * Pure event-to-cache reducer. Exported for tests; the React hook below
 * supplies real React Query operations as the `ops` argument.
 */
export function dispatchTodayBoardEvent(
  event: RtEvent,
  tenantId: number | undefined,
  ops: DispatcherOps,
): void {
  if (tenantId !== undefined && event.tenant_id !== tenantId) return;
  switch (event.type) {
    case 'schedule.optimized': {
      ops.invalidateVisits();
      return;
    }
    case 'visit.reassigned': {
      const { visit_id, clinician_id } = event.payload as {
        visit_id: number;
        clinician_id: number;
      };
      ops.setVisits((current) =>
        current?.map((v) => (v.id === visit_id ? { ...v, clinician: clinician_id } : v)),
      );
      return;
    }
    case 'visit.status_changed': {
      const { visit_id, status, clinician_id } = event.payload as {
        visit_id: number;
        status: string;
        clinician_id: number | null;
      };
      ops.setVisits((current) =>
        current?.map((v) =>
          v.id === visit_id ? { ...v, status, clinician: clinician_id } : v,
        ),
      );
      return;
    }
    default:
      return;
  }
}

export function useTodayBoard(tenantId: number | undefined) {
  const qc = useQueryClient();
  const visits = useQuery({ queryKey: VISITS_KEY, queryFn: () => fetchList<Visit>('/api/v1/visits/') });
  const clinicians = useQuery({
    queryKey: CLINICIANS_KEY,
    queryFn: () => fetchList<Clinician>('/api/v1/clinicians/'),
  });

  const handler = useCallback(
    (event: RtEvent) => {
      dispatchTodayBoardEvent(event, tenantId, {
        setVisits: (updater) =>
          qc.setQueryData<Visit[]>(VISITS_KEY, (current) => updater(current) ?? current),
        invalidateVisits: () => qc.invalidateQueries({ queryKey: VISITS_KEY }),
      });
    },
    [qc, tenantId],
  );
  useRealtimeEvents(handler);

  return { visits, clinicians };
}
