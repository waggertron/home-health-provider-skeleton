import { describe, expect, it, vi } from 'vitest';
import {
  dispatchPositionEvent,
  type ClinicianPosition,
  type PositionDispatcherOps,
} from './useClinicianPositions';
import type { RtEvent } from './useRealtimeEvents';

function newOps() {
  let cache: ClinicianPosition[] | undefined;
  const ops: PositionDispatcherOps = {
    upsert: (updater) => {
      cache = updater(cache);
    },
  };
  return {
    ops,
    seed(rows: ClinicianPosition[]) {
      cache = rows;
    },
    snapshot() {
      return cache;
    },
  };
}

function event(payload: Record<string, unknown>, tenant_id = 1): RtEvent {
  return { type: 'clinician.position_updated', tenant_id, ts: 't', payload };
}

describe('dispatchPositionEvent', () => {
  it('inserts the first frame for a clinician into an empty cache', () => {
    const w = newOps();
    dispatchPositionEvent(
      event({ clinician_id: 7, lat: 34.0, lon: -118.0, ts: 'T' }),
      1,
      w.ops,
    );
    expect(w.snapshot()).toEqual([{ clinician: 7, lat: 34.0, lon: -118.0, ts: 'T' }]);
  });

  it('replaces in place when a clinician already has a row', () => {
    const w = newOps();
    w.seed([{ clinician: 7, lat: 34.0, lon: -118.0, ts: 'T' }]);
    dispatchPositionEvent(
      event({ clinician_id: 7, lat: 34.05, lon: -118.05, ts: 'T2' }),
      1,
      w.ops,
    );
    expect(w.snapshot()).toEqual([{ clinician: 7, lat: 34.05, lon: -118.05, ts: 'T2' }]);
  });

  it('appends a row when a different clinician reports', () => {
    const w = newOps();
    w.seed([{ clinician: 7, lat: 34.0, lon: -118.0, ts: 'T' }]);
    dispatchPositionEvent(
      event({ clinician_id: 9, lat: 34.1, lon: -118.1, ts: 'T2' }),
      1,
      w.ops,
    );
    expect(w.snapshot()?.length).toBe(2);
  });

  it('ignores frames for other tenants', () => {
    const w = newOps();
    const upsert = vi.spyOn(w.ops, 'upsert');
    dispatchPositionEvent(
      event({ clinician_id: 7, lat: 0, lon: 0, ts: 'T' }, /*tenant_id*/ 2),
      1,
      w.ops,
    );
    expect(upsert).not.toHaveBeenCalled();
  });

  it('ignores other event types', () => {
    const w = newOps();
    const upsert = vi.spyOn(w.ops, 'upsert');
    dispatchPositionEvent(
      { type: 'visit.reassigned', tenant_id: 1, ts: 't', payload: {} },
      1,
      w.ops,
    );
    expect(upsert).not.toHaveBeenCalled();
  });
});
