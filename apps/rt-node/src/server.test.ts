import { EventEmitter } from 'node:events';
import jwt from 'jsonwebtoken';
import { describe, expect, it, vi } from 'vitest';
import { SubscriberManager } from './redis.js';
import { attachConnection } from './server.js';

const KEY = 'test-signing-key-at-least-32-bytes-xxxxxxxxxxxxxxxxxxxx';

function fakeWs() {
  const ws = new EventEmitter() as EventEmitter & {
    send: ReturnType<typeof vi.fn>;
    close: ReturnType<typeof vi.fn>;
    terminate: ReturnType<typeof vi.fn>;
  };
  ws.send = vi.fn();
  ws.close = vi.fn();
  ws.terminate = vi.fn();
  return ws;
}

function fakeRedis() {
  const ee = new EventEmitter() as EventEmitter & {
    subscribe: ReturnType<typeof vi.fn>;
    unsubscribe: ReturnType<typeof vi.fn>;
  };
  ee.subscribe = vi.fn(async () => {});
  ee.unsubscribe = vi.fn(async () => {});
  return ee;
}

function mint(claims: Record<string, unknown> = {}): string {
  return jwt.sign({ tenant_id: 1, role: 'scheduler', scope: 'ws', ...claims }, KEY, {
    expiresIn: 60,
  });
}

/** Advance enough microtasks for the async subscribe to settle. */
async function flushMicro() {
  await new Promise((r) => setImmediate(r));
  await new Promise((r) => setImmediate(r));
}

describe('attachConnection', () => {
  it('auths then forwards redis messages to the ws', async () => {
    const redis = fakeRedis();
    const subs = new SubscriberManager(redis as never);
    const ws = fakeWs();
    attachConnection(ws as never, subs, KEY);

    ws.emit('message', Buffer.from(JSON.stringify({ type: 'auth', token: mint() })));
    await flushMicro();

    redis.emit('message', 'tenant:1:events', '{"type":"visit.status_changed"}');
    expect(ws.send).toHaveBeenCalledWith(JSON.stringify({ type: 'hello', tenant_id: 1 }));
    expect(ws.send).toHaveBeenCalledWith('{"type":"visit.status_changed"}');
  });

  it('closes with 4401 on bad auth', async () => {
    const subs = new SubscriberManager(fakeRedis() as never);
    const ws = fakeWs();
    attachConnection(ws as never, subs, KEY);
    ws.emit('message', Buffer.from(JSON.stringify({ type: 'auth', token: 'garbage' })));
    await flushMicro();
    expect(ws.close).toHaveBeenCalledWith(4401, 'auth failed');
  });

  it('unsubscribes on close (last-subscriber pattern)', async () => {
    const redis = fakeRedis();
    const subs = new SubscriberManager(redis as never);
    const ws = fakeWs();
    attachConnection(ws as never, subs, KEY);
    ws.emit(
      'message',
      Buffer.from(JSON.stringify({ type: 'auth', token: mint({ tenant_id: 2, role: 'admin' }) })),
    );
    await flushMicro();
    ws.emit('close');
    await flushMicro();
    expect(redis.unsubscribe).toHaveBeenCalledWith('tenant:2:events');
  });

  it('ignores non-auth frames before auth', async () => {
    const redis = fakeRedis();
    const subs = new SubscriberManager(redis as never);
    const ws = fakeWs();
    attachConnection(ws as never, subs, KEY);
    ws.emit('message', Buffer.from(JSON.stringify({ type: 'pong' })));
    ws.emit('message', Buffer.from('{"not":"json-but-close"}'));
    await flushMicro();
    expect(redis.subscribe).not.toHaveBeenCalled();
    expect(ws.close).not.toHaveBeenCalled();
  });

  it('pong frame arrives before auth and is a no-op', async () => {
    const redis = fakeRedis();
    const subs = new SubscriberManager(redis as never);
    const ws = fakeWs();
    attachConnection(ws as never, subs, KEY);
    ws.emit('message', Buffer.from(JSON.stringify({ type: 'pong' })));
    await flushMicro();
    expect(ws.send).not.toHaveBeenCalled();
  });
});
