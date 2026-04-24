/**
 * Integration tests: real WebSocket server + real WebSocket client, with a
 * minimal in-process fake for ioredis. Covers healthz, auth, fan-out,
 * multi-client, tenant isolation, pong resets heartbeat, and bad-auth close.
 */
import { EventEmitter } from 'node:events';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import WebSocket from 'ws';
import jwt from 'jsonwebtoken';
import type Redis from 'ioredis';
import { createServer, type RtServer } from './server.js';

const KEY = 'test-signing-key-at-least-32-bytes-xxxxxxxxxxxxxxxxxxxx';

function fakeIoRedis() {
  const ee = new EventEmitter() as EventEmitter & {
    subscribe: (channel: string) => Promise<void>;
    unsubscribe: (channel: string) => Promise<void>;
    quit: () => Promise<void>;
    emitMessage: (channel: string, message: string) => void;
  };
  ee.subscribe = vi.fn(async () => {});
  ee.unsubscribe = vi.fn(async () => {});
  ee.quit = vi.fn(async () => {});
  ee.emitMessage = (channel, message) => ee.emit('message', channel, message);
  return ee;
}

function mint(overrides: Record<string, unknown> = {}, expiresIn = 60): string {
  return jwt.sign(
    { tenant_id: 1, role: 'scheduler', scope: 'ws', ...overrides },
    KEY,
    { expiresIn },
  );
}

async function waitForOpen(ws: WebSocket): Promise<void> {
  await new Promise<void>((resolve, reject) => {
    ws.once('open', () => resolve());
    ws.once('error', reject);
  });
}

async function readFrame(ws: WebSocket, predicate: (msg: any) => boolean, timeoutMs = 1000): Promise<any> {
  return new Promise((resolve, reject) => {
    const onMessage = (raw: WebSocket.RawData) => {
      try {
        const msg = JSON.parse(raw.toString());
        if (predicate(msg)) {
          ws.off('message', onMessage);
          clearTimeout(timer);
          resolve(msg);
        }
      } catch {
        // ignore
      }
    };
    const timer = setTimeout(() => {
      ws.off('message', onMessage);
      reject(new Error('timed out waiting for frame'));
    }, timeoutMs);
    ws.on('message', onMessage);
  });
}

describe('rt-node integration', () => {
  let server: RtServer;
  let redis: ReturnType<typeof fakeIoRedis>;
  let url: string;

  beforeEach(async () => {
    redis = fakeIoRedis();
    server = createServer({
      signingKey: KEY,
      redis: redis as unknown as Redis,
      connection: { intervalMs: 50, timeoutMs: 300 },
    });
    await new Promise<void>((resolve) => server.httpServer.listen(0, resolve));
    const addr = server.httpServer.address();
    if (!addr || typeof addr === 'string') throw new Error('no address');
    url = `ws://127.0.0.1:${addr.port}`;
  });

  afterEach(async () => {
    await server.close();
  });

  it('GET /healthz returns 200 ok', async () => {
    const addr = server.httpServer.address();
    if (!addr || typeof addr === 'string') throw new Error('no address');
    const res = await fetch(`http://127.0.0.1:${addr.port}/healthz`);
    expect(res.status).toBe(200);
    expect(await res.text()).toBe('ok');
  });

  it('GET /unknown returns 404', async () => {
    const addr = server.httpServer.address();
    if (!addr || typeof addr === 'string') throw new Error('no address');
    const res = await fetch(`http://127.0.0.1:${addr.port}/bogus`);
    expect(res.status).toBe(404);
  });

  it('auth → subscribe → receive fan-out', async () => {
    const ws = new WebSocket(`${url}/ws`);
    await waitForOpen(ws);
    ws.send(JSON.stringify({ type: 'auth', token: mint() }));
    const hello = await readFrame(ws, (m) => m.type === 'hello');
    expect(hello.tenant_id).toBe(1);

    redis.emitMessage('tenant:1:events', JSON.stringify({ type: 'visit.status_changed', tenant_id: 1, payload: { x: 1 } }));
    const msg = await readFrame(ws, (m) => m.type === 'visit.status_changed');
    expect(msg.payload).toEqual({ x: 1 });
    ws.close();
  });

  it('two clients on same tenant both receive the message', async () => {
    const a = new WebSocket(`${url}/ws`);
    const b = new WebSocket(`${url}/ws`);
    await Promise.all([waitForOpen(a), waitForOpen(b)]);
    const token = mint();
    a.send(JSON.stringify({ type: 'auth', token }));
    b.send(JSON.stringify({ type: 'auth', token }));
    await Promise.all([
      readFrame(a, (m) => m.type === 'hello'),
      readFrame(b, (m) => m.type === 'hello'),
    ]);

    redis.emitMessage('tenant:1:events', JSON.stringify({ type: 'fanout' }));
    await Promise.all([
      readFrame(a, (m) => m.type === 'fanout'),
      readFrame(b, (m) => m.type === 'fanout'),
    ]);
    a.close();
    b.close();
  });

  it('clients on different tenants are isolated', async () => {
    const a = new WebSocket(`${url}/ws`);
    const b = new WebSocket(`${url}/ws`);
    await Promise.all([waitForOpen(a), waitForOpen(b)]);
    a.send(JSON.stringify({ type: 'auth', token: mint({ tenant_id: 1 }) }));
    b.send(JSON.stringify({ type: 'auth', token: mint({ tenant_id: 2 }) }));
    await Promise.all([
      readFrame(a, (m) => m.type === 'hello'),
      readFrame(b, (m) => m.type === 'hello'),
    ]);

    // Capture whatever B sees in a window.
    const bSeen: string[] = [];
    b.on('message', (raw) => {
      try {
        const m = JSON.parse(raw.toString());
        if (m.type !== 'hello' && m.type !== 'ping') bSeen.push(m.type);
      } catch { /* ignore */ }
    });

    redis.emitMessage('tenant:1:events', JSON.stringify({ type: 'only.for.a' }));
    await readFrame(a, (m) => m.type === 'only.for.a');
    await new Promise((r) => setTimeout(r, 100));
    expect(bSeen).toEqual([]);
    a.close();
    b.close();
  });

  it('bad auth closes the socket with code 4401', async () => {
    const ws = new WebSocket(`${url}/ws`);
    await waitForOpen(ws);
    ws.send(JSON.stringify({ type: 'auth', token: 'garbage' }));
    const code: number = await new Promise((resolve) => {
      ws.once('close', (c) => resolve(c));
    });
    expect(code).toBe(4401);
  });

  it('pong replies keep the socket alive across the timeout window', async () => {
    const ws = new WebSocket(`${url}/ws`);
    await waitForOpen(ws);
    ws.send(JSON.stringify({ type: 'auth', token: mint() }));
    await readFrame(ws, (m) => m.type === 'hello');

    // Server is configured to ping every 50ms and timeout after 300ms.
    // Respond to every ping with a pong; socket must stay open ≥ 400ms.
    ws.on('message', (raw) => {
      try {
        const m = JSON.parse(raw.toString());
        if (m.type === 'ping') ws.send(JSON.stringify({ type: 'pong' }));
      } catch { /* ignore */ }
    });
    await new Promise((r) => setTimeout(r, 400));
    expect(ws.readyState).toBe(WebSocket.OPEN);
    ws.close();
  });

  it('silent socket is terminated after timeoutMs', async () => {
    const ws = new WebSocket(`${url}/ws`);
    await waitForOpen(ws);
    ws.send(JSON.stringify({ type: 'auth', token: mint() }));
    await readFrame(ws, (m) => m.type === 'hello');
    // Deliberately do not respond to pings.
    await new Promise<void>((resolve) => ws.on('close', () => resolve()));
    expect(ws.readyState).toBe(WebSocket.CLOSED);
  });
});
