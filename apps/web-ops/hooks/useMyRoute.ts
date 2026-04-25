'use client';

import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useCallback } from 'react';
import { apiFetch } from '@/lib/api';
import type { Visit } from './useTodayBoard';
import type { RtEvent } from './useRealtimeEvents';
import { useRealtimeEvents } from './useRealtimeEvents';

export const MY_VISITS_KEY = ['visits', 'mine'] as const;

async function fetchMyVisits(clinicianId: number): Promise<Visit[]> {
  const r = await apiFetch('/api/v1/visits/');
  if (!r.ok) throw new Error(`visits: ${r.status}`);
  const data = (await r.json()) as Visit[] | { results: Visit[] };
  const all = Array.isArray(data) ? data : data.results;
  return all
    .filter((v) => v.clinician === clinicianId)
    .sort((a, b) => {
      const ao = a.ordering_seq ?? 1e9;
      const bo = b.ordering_seq ?? 1e9;
      if (ao !== bo) return ao - bo;
      return a.window_start.localeCompare(b.window_start);
    });
}

export interface MyRouteDispatcherOps {
  setMyVisits(updater: (current: Visit[] | undefined) => Visit[] | undefined): void;
}

/**
 * Pure event-to-cache reducer for the clinician's view. Filters to events
 * touching this clinician's own visits.
 */
export function dispatchMyRouteEvent(
  event: RtEvent,
  tenantId: number | undefined,
  clinicianId: number,
  ops: MyRouteDispatcherOps,
): void {
  if (tenantId !== undefined && event.tenant_id !== tenantId) return;
  if (event.type === 'visit.status_changed') {
    const { visit_id, status, clinician_id } = event.payload as {
      visit_id: number;
      status: string;
      clinician_id: number | null;
    };
    ops.setMyVisits((current) =>
      current?.map((v) => (v.id === visit_id ? { ...v, status, clinician: clinician_id } : v)),
    );
    return;
  }
  if (event.type === 'visit.reassigned') {
    const { visit_id, clinician_id } = event.payload as {
      visit_id: number;
      clinician_id: number;
    };
    ops.setMyVisits((current) => {
      if (!current) return current;
      // If reassigned away from me, drop the row; if reassigned to me, leave
      // the cache alone (the next query refresh will pull it in fresh).
      if (clinician_id === clinicianId) return current;
      return current.filter((v) => v.id !== visit_id);
    });
  }
}

export function useMyRoute(clinicianId: number | undefined, tenantId: number | undefined) {
  const qc = useQueryClient();
  const visits = useQuery({
    queryKey: MY_VISITS_KEY,
    queryFn: () => fetchMyVisits(clinicianId ?? -1),
    enabled: clinicianId !== undefined,
  });

  const handler = useCallback(
    (event: RtEvent) => {
      if (clinicianId === undefined) return;
      dispatchMyRouteEvent(event, tenantId, clinicianId, {
        setMyVisits: (updater) =>
          qc.setQueryData<Visit[]>(MY_VISITS_KEY, (current) => updater(current) ?? current),
      });
    },
    [qc, tenantId, clinicianId],
  );
  useRealtimeEvents(handler);

  return visits;
}
