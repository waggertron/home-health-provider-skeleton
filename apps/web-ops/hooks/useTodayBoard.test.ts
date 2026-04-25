import { describe, expect, it, vi } from 'vitest';
import type { RtEvent } from './useRealtimeEvents';
import { dispatchTodayBoardEvent, type DispatcherOps, type Visit } from './useTodayBoard';

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

function newOps() {
  let cache: Visit[] | undefined;
  const ops: DispatcherOps = {
    setVisits: (updater) => {
      cache = updater(cache);
    },
    invalidateVisits: vi.fn(),
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

describe('dispatchTodayBoardEvent', () => {
  it('schedule.optimized → invalidates the visits query', () => {
    const { ops } = newOps();
    dispatchTodayBoardEvent(event('schedule.optimized', { date: '2026-04-24' }), 1, ops);
    expect(ops.invalidateVisits).toHaveBeenCalledTimes(1);
  });

  it('visit.reassigned → patches the visit row in place', () => {
    const w = newOps();
    w.seed([visit({ id: 42, clinician: null }), visit({ id: 7 })]);
    dispatchTodayBoardEvent(
      event('visit.reassigned', { visit_id: 42, clinician_id: 17 }),
      1,
      w.ops,
    );
    expect(w.snapshot()?.find((v) => v.id === 42)?.clinician).toBe(17);
    expect(w.snapshot()?.find((v) => v.id === 7)?.clinician).toBeNull();
  });

  it('visit.status_changed → updates status and clinician', () => {
    const w = newOps();
    w.seed([visit({ id: 5, status: 'assigned', clinician: 17 })]);
    dispatchTodayBoardEvent(
      event('visit.status_changed', { visit_id: 5, status: 'on_site', clinician_id: 17 }),
      1,
      w.ops,
    );
    expect(w.snapshot()?.[0]?.status).toBe('on_site');
  });

  it('events for other tenants are ignored', () => {
    const w = newOps();
    w.seed([visit({ id: 1, clinician: null })]);
    dispatchTodayBoardEvent(
      event('visit.reassigned', { visit_id: 1, clinician_id: 99 }, /*tenant_id=*/ 2),
      1,
      w.ops,
    );
    expect(w.snapshot()?.[0]?.clinician).toBeNull();
    expect(w.ops.invalidateVisits).not.toHaveBeenCalled();
  });

  it('unknown event types are no-ops', () => {
    const w = newOps();
    w.seed([visit()]);
    dispatchTodayBoardEvent(event('clinician.position_updated', {}), 1, w.ops);
    expect(w.ops.invalidateVisits).not.toHaveBeenCalled();
    expect(w.snapshot()?.[0]?.id).toBe(1);
  });

  it('skips when the cache is empty (no current visits to patch)', () => {
    const w = newOps();
    dispatchTodayBoardEvent(
      event('visit.reassigned', { visit_id: 1, clinician_id: 17 }),
      1,
      w.ops,
    );
    // No throw — cache remains undefined.
    expect(w.snapshot()).toBeUndefined();
  });
});
