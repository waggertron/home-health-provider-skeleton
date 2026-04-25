'use client';

import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useCallback } from 'react';
import { apiFetch } from '@/lib/api';
import type { RtEvent } from './useRealtimeEvents';
import { useRealtimeEvents } from './useRealtimeEvents';

export interface ClinicianPosition {
  id?: number;
  clinician: number;
  lat: number;
  lon: number;
  ts: string;
  heading?: number | null;
  speed?: number | null;
}

export const POSITIONS_KEY = ['positions', 'latest'] as const;

async function fetchLatest(): Promise<ClinicianPosition[]> {
  const r = await apiFetch('/api/v1/positions/latest/');
  if (!r.ok) throw new Error(`positions: ${r.status}`);
  const data = (await r.json()) as ClinicianPosition[] | { results: ClinicianPosition[] };
  return Array.isArray(data) ? data : data.results;
}

export interface PositionDispatcherOps {
  upsert(updater: (current: ClinicianPosition[] | undefined) => ClinicianPosition[] | undefined): void;
}

export function dispatchPositionEvent(
  event: RtEvent,
  tenantId: number | undefined,
  ops: PositionDispatcherOps,
): void {
  if (tenantId !== undefined && event.tenant_id !== tenantId) return;
  if (event.type !== 'clinician.position_updated') return;
  const { clinician_id, lat, lon, ts } = event.payload as {
    clinician_id: number;
    lat: number;
    lon: number;
    ts: string;
  };
  ops.upsert((current) => {
    const next: ClinicianPosition = { clinician: clinician_id, lat, lon, ts };
    if (!current) return [next];
    const idx = current.findIndex((p) => p.clinician === clinician_id);
    if (idx === -1) return [...current, next];
    const copy = current.slice();
    copy[idx] = next;
    return copy;
  });
}

export function useClinicianPositions(tenantId: number | undefined) {
  const qc = useQueryClient();
  const positions = useQuery({ queryKey: POSITIONS_KEY, queryFn: fetchLatest });

  const handler = useCallback(
    (event: RtEvent) => {
      dispatchPositionEvent(event, tenantId, {
        upsert: (updater) => qc.setQueryData<ClinicianPosition[]>(POSITIONS_KEY, updater),
      });
    },
    [qc, tenantId],
  );
  useRealtimeEvents(handler);

  return positions;
}
