import { describe, expect, it } from 'vitest';
import {
  dispatchMyRouteEvent,
  type MyRouteDispatcherOps,
} from './useMyRoute';
import type { RtEvent } from './useRealtimeEvents';
import type { Visit } from './useTodayBoard';

function visit(overrides: Partial<Visit> = {}): Visit {
  return {
    id: 1,
    patient: 1,
    clinician: 7,
    status: 'assigned',
    required_skill: 'RN',
    window_start: '2026-04-24T08:00:00Z',
    window_end: '2026-04-24T10:00:00Z',
    ordering_seq: 0,
    ...overrides,
  };
}

function newOps() {
  let cache: Visit[] | undefined;
  const ops: MyRouteDispatcherOps = {
    setMyVisits: (updater) => {
      cache = updater(cache);
    },
  };
  return {
    ops,
    seed(rows: Visit[]) {
      cache = rows;
    },
    snapshot() {
      return cache;
    },
  };
}

function event(type: string, payload: Record<string, unknown>, tenant_id = 1): RtEvent {
  return { type, tenant_id, ts: 't', payload };
}

describe('dispatchMyRouteEvent', () => {
  const MY_CLINICIAN = 7;

  it('visit.status_changed → patches the matching row', () => {
    const w = newOps();
    w.seed([visit({ id: 1, status: 'assigned' })]);
    dispatchMyRouteEvent(
      event('visit.status_changed', { visit_id: 1, status: 'on_site', clinician_id: 7 }),
      1,
      MY_CLINICIAN,
      w.ops,
    );
    expect(w.snapshot()?.[0]?.status).toBe('on_site');
  });

  it('visit.reassigned away from me → drops the row from my route', () => {
    const w = newOps();
    w.seed([visit({ id: 1 }), visit({ id: 2 })]);
    dispatchMyRouteEvent(
      event('visit.reassigned', { visit_id: 1, clinician_id: 99 }),
      1,
      MY_CLINICIAN,
      w.ops,
    );
    expect(w.snapshot()?.map((v) => v.id)).toEqual([2]);
  });

  it('visit.reassigned to me leaves the cache alone (refresh picks it up)', () => {
    const w = newOps();
    w.seed([visit({ id: 1 })]);
    dispatchMyRouteEvent(
      event('visit.reassigned', { visit_id: 99, clinician_id: 7 }),
      1,
      MY_CLINICIAN,
      w.ops,
    );
    expect(w.snapshot()?.length).toBe(1);
  });

  it('events for other tenants are ignored', () => {
    const w = newOps();
    w.seed([visit({ id: 1, status: 'assigned' })]);
    dispatchMyRouteEvent(
      event('visit.status_changed', { visit_id: 1, status: 'on_site', clinician_id: 7 }, 2),
      1,
      MY_CLINICIAN,
      w.ops,
    );
    expect(w.snapshot()?.[0]?.status).toBe('assigned');
  });

  it('schedule.optimized is ignored at the clinician layer', () => {
    const w = newOps();
    w.seed([visit({ id: 1 })]);
    dispatchMyRouteEvent(
      event('schedule.optimized', { date: '2026-04-24' }),
      1,
      MY_CLINICIAN,
      w.ops,
    );
    expect(w.snapshot()?.length).toBe(1);
  });
});
