import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { RtClient, type EventHandler } from './useRealtimeEvents';

/**
 * Minimal fake WebSocket implementation. Browser EventTarget API isn't
 * required — RtClient only uses on{open,message,close,error} + send + close.
 */
class FakeWebSocket {
  static instances: FakeWebSocket[] = [];
  static last(): FakeWebSocket {
    return FakeWebSocket.instances[FakeWebSocket.instances.length - 1]!;
  }

  readonly url: string;
  onopen: (() => void) | null = null;
  onmessage: ((ev: MessageEvent) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  sent: string[] = [];

  constructor(url: string) {
    this.url = url;
    FakeWebSocket.instances.push(this);
  }

  send(data: string): void {
    this.sent.push(data);
  }

  close(): void {
    this.onclose?.();
  }

  /** Test helper: simulate the server "opening" the socket. */
  fireOpen(): void {
    this.onopen?.();
  }

  /** Test helper: simulate an inbound message. */
  fireMessage(payload: unknown): void {
    this.onmessage?.({ data: JSON.stringify(payload) } as MessageEvent);
  }

  fireClose(): void {
    this.onclose?.();
  }
}

function newClient(opts: Partial<ConstructorParameters<typeof RtClient>[0]> = {}) {
  return new RtClient({
    url: 'ws://test',
    mintToken: async () => 'TOK',
    WebSocketImpl: FakeWebSocket as unknown as typeof WebSocket,
    reconnectMinMs: 10,
    reconnectMaxMs: 100,
    ...opts,
  });
}

describe('RtClient', () => {
  beforeEach(() => {
    FakeWebSocket.instances = [];
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it('sends auth frame on open', async () => {
    const client = newClient();
    client.start();
    await Promise.resolve(); // mintToken resolves
    await Promise.resolve();
    FakeWebSocket.last().fireOpen();
    expect(FakeWebSocket.last().sent[0]).toBe(JSON.stringify({ type: 'auth', token: 'TOK' }));
    client.stop();
  });

  it('dispatches domain events to subscribers', async () => {
    const handler = vi.fn();
    const client = newClient();
    client.on(handler);
    client.start();
    await Promise.resolve();
    await Promise.resolve();
    const ws = FakeWebSocket.last();
    ws.fireOpen();
    ws.fireMessage({ type: 'hello', tenant_id: 1 });
    ws.fireMessage({
      type: 'schedule.optimized',
      tenant_id: 1,
      ts: 't',
      payload: { date: '2026-04-24', routes: 16 },
    });
    expect(handler).toHaveBeenCalledTimes(1);
    const event = handler.mock.calls[0]![0];
    expect(event.type).toBe('schedule.optimized');
    expect(event.payload.routes).toBe(16);
    client.stop();
  });

  it('auto-replies pong when the server pings', async () => {
    const client = newClient();
    client.start();
    await Promise.resolve();
    await Promise.resolve();
    const ws = FakeWebSocket.last();
    ws.fireOpen();
    ws.fireMessage({ type: 'ping' });
    expect(ws.sent).toContain(JSON.stringify({ type: 'pong' }));
    client.stop();
  });

  it('multiple handlers each receive the same event', async () => {
    const a = vi.fn();
    const b = vi.fn();
    const client = newClient();
    client.on(a);
    client.on(b);
    client.start();
    await Promise.resolve();
    await Promise.resolve();
    FakeWebSocket.last().fireOpen();
    FakeWebSocket.last().fireMessage({
      type: 'visit.reassigned',
      tenant_id: 1,
      ts: 't',
      payload: { visit_id: 1 },
    });
    expect(a).toHaveBeenCalledTimes(1);
    expect(b).toHaveBeenCalledTimes(1);
    client.stop();
  });

  it('off() removes a handler', async () => {
    const handler = vi.fn();
    const client = newClient();
    const off = client.on(handler);
    client.start();
    await Promise.resolve();
    await Promise.resolve();
    FakeWebSocket.last().fireOpen();
    off();
    FakeWebSocket.last().fireMessage({ type: 'visit.reassigned', tenant_id: 1, ts: 't', payload: {} });
    expect(handler).not.toHaveBeenCalled();
    client.stop();
  });

  it('ignores malformed frames', async () => {
    const handler = vi.fn();
    const client = newClient();
    client.on(handler);
    client.start();
    await Promise.resolve();
    await Promise.resolve();
    const ws = FakeWebSocket.last();
    ws.fireOpen();
    ws.onmessage?.({ data: 'not-json' } as MessageEvent);
    ws.onmessage?.({ data: JSON.stringify(null) } as MessageEvent);
    ws.onmessage?.({ data: JSON.stringify({ no_type: true }) } as MessageEvent);
    expect(handler).not.toHaveBeenCalled();
    client.stop();
  });

  it('reconnects with exponential backoff after the socket closes', async () => {
    vi.useFakeTimers();
    const client = newClient({ reconnectMinMs: 100, reconnectMaxMs: 1000 });
    client.start();
    await vi.runAllTimersAsync(); // resolve mintToken
    FakeWebSocket.last().fireOpen();
    FakeWebSocket.last().fireClose();
    expect(FakeWebSocket.instances.length).toBe(1);
    await vi.advanceTimersByTimeAsync(120);
    await vi.runAllTimersAsync();
    expect(FakeWebSocket.instances.length).toBe(2);
    client.stop();
  });

  it('stop() cancels pending reconnect', async () => {
    vi.useFakeTimers();
    const client = newClient({ reconnectMinMs: 100, reconnectMaxMs: 1000 });
    client.start();
    await vi.runAllTimersAsync();
    FakeWebSocket.last().fireOpen();
    FakeWebSocket.last().fireClose();
    client.stop();
    await vi.advanceTimersByTimeAsync(500);
    expect(FakeWebSocket.instances.length).toBe(1);
  });
});
