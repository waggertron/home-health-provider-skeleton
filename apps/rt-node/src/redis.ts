import type Redis from 'ioredis';

export type MessageHandler = (message: string) => void;

/**
 * Lazily subscribes to Redis channels. First handler triggers a Redis
 * SUBSCRIBE; removing the last handler triggers UNSUBSCRIBE. Multiple
 * handlers for the same channel share a single Redis subscription.
 */
export class SubscriberManager {
  private readonly handlers = new Map<string, Set<MessageHandler>>();

  constructor(private readonly redis: Redis) {
    this.redis.on('message', (channel: string, message: string) => {
      const set = this.handlers.get(channel);
      if (!set) return;
      for (const h of set) h(message);
    });
  }

  async subscribe(channel: string, handler: MessageHandler): Promise<void> {
    let set = this.handlers.get(channel);
    if (!set) {
      set = new Set();
      this.handlers.set(channel, set);
      await this.redis.subscribe(channel);
    }
    set.add(handler);
  }

  async unsubscribe(channel: string, handler: MessageHandler): Promise<void> {
    const set = this.handlers.get(channel);
    if (!set) return;
    set.delete(handler);
    if (set.size === 0) {
      this.handlers.delete(channel);
      await this.redis.unsubscribe(channel);
    }
  }

  channelCount(): number {
    return this.handlers.size;
  }

  handlerCount(channel: string): number {
    return this.handlers.get(channel)?.size ?? 0;
  }
}
