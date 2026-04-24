import { EventEmitter } from 'node:events';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { Heartbeat } from './heartbeat.js';

function fakeWs() {
  const ws = new EventEmitter() as EventEmitter & {
    send: ReturnType<typeof vi.fn>;
    terminate: ReturnType<typeof vi.fn>;
  };
  ws.send = vi.fn();
  ws.terminate = vi.fn();
  return ws;
}

describe('Heartbeat', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it('sends {type:"ping"} every intervalMs', () => {
    const ws = fakeWs();
    const hb = new Heartbeat({ ws: ws as never, intervalMs: 100, timeoutMs: 1000 });
    hb.start();
    vi.advanceTimersByTime(100);
    expect(ws.send).toHaveBeenCalledWith(JSON.stringify({ type: 'ping' }));
    vi.advanceTimersByTime(100);
    expect(ws.send).toHaveBeenCalledTimes(2);
    hb.stop();
  });

  it('terminates when pong gap exceeds timeoutMs', () => {
    const ws = fakeWs();
    const hb = new Heartbeat({ ws: ws as never, intervalMs: 100, timeoutMs: 250 });
    hb.start();
    vi.advanceTimersByTime(100); // tick 1 — elapsed 100, ok
    vi.advanceTimersByTime(100); // tick 2 — elapsed 200, ok
    vi.advanceTimersByTime(100); // tick 3 — elapsed 300 > 250, terminate
    expect(ws.terminate).toHaveBeenCalled();
  });

  it('markPong resets the pong clock so the socket stays alive', () => {
    const ws = fakeWs();
    const hb = new Heartbeat({ ws: ws as never, intervalMs: 100, timeoutMs: 250 });
    hb.start();
    vi.advanceTimersByTime(200);
    hb.markPong();
    vi.advanceTimersByTime(200);
    expect(ws.terminate).not.toHaveBeenCalled();
    hb.stop();
  });

  it('stop cancels further ticks', () => {
    const ws = fakeWs();
    const hb = new Heartbeat({ ws: ws as never, intervalMs: 100, timeoutMs: 1000 });
    hb.start();
    hb.stop();
    vi.advanceTimersByTime(500);
    expect(ws.send).not.toHaveBeenCalled();
  });
});
