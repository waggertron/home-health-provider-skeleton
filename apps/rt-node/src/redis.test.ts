import { EventEmitter } from 'node:events';
import { describe, expect, it, vi } from 'vitest';
import { SubscriberManager } from './redis.js';

/** Minimal ioredis-shaped mock: EventEmitter plus subscribe/unsubscribe spies. */
function fakeRedis() {
  const ee = new EventEmitter() as EventEmitter & {
    subscribe: (channel: string) => Promise<void>;
    unsubscribe: (channel: string) => Promise<void>;
  };
  ee.subscribe = vi.fn(async () => {});
  ee.unsubscribe = vi.fn(async () => {});
  return ee;
}

describe('SubscriberManager', () => {
  it('first subscribe to a channel calls redis.subscribe', async () => {
    const r = fakeRedis();
    const subs = new SubscriberManager(r as never);
    await subs.subscribe('tenant:1:events', () => {});
    expect(r.subscribe).toHaveBeenCalledWith('tenant:1:events');
    expect(subs.handlerCount('tenant:1:events')).toBe(1);
  });

  it('second subscribe does not re-call redis.subscribe', async () => {
    const r = fakeRedis();
    const subs = new SubscriberManager(r as never);
    await subs.subscribe('tenant:1:events', () => {});
    await subs.subscribe('tenant:1:events', () => {});
    expect(r.subscribe).toHaveBeenCalledTimes(1);
    expect(subs.handlerCount('tenant:1:events')).toBe(2);
  });

  it('unsubscribe removes a handler without touching redis until last', async () => {
    const r = fakeRedis();
    const subs = new SubscriberManager(r as never);
    const h1 = () => {};
    const h2 = () => {};
    await subs.subscribe('tenant:1:events', h1);
    await subs.subscribe('tenant:1:events', h2);
    await subs.unsubscribe('tenant:1:events', h1);
    expect(r.unsubscribe).not.toHaveBeenCalled();
    await subs.unsubscribe('tenant:1:events', h2);
    expect(r.unsubscribe).toHaveBeenCalledWith('tenant:1:events');
    expect(subs.channelCount()).toBe(0);
  });

  it('message on redis fans out to every handler of that channel', async () => {
    const r = fakeRedis();
    const subs = new SubscriberManager(r as never);
    const seen: string[] = [];
    await subs.subscribe('tenant:1:events', (m) => seen.push(`a:${m}`));
    await subs.subscribe('tenant:1:events', (m) => seen.push(`b:${m}`));
    r.emit('message', 'tenant:1:events', '{"type":"x"}');
    expect(seen).toEqual(['a:{"type":"x"}', 'b:{"type":"x"}']);
  });

  it('message on an unrelated channel is ignored', async () => {
    const r = fakeRedis();
    const subs = new SubscriberManager(r as never);
    const seen: string[] = [];
    await subs.subscribe('tenant:1:events', (m) => seen.push(m));
    r.emit('message', 'tenant:2:events', '{"type":"x"}');
    expect(seen).toEqual([]);
  });
});
