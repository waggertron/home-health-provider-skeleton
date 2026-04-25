'use client';

import { useEffect } from 'react';
import { wsToken } from '@/lib/api';

const RT_URL =
  (typeof process !== 'undefined' && process.env.NEXT_PUBLIC_RT_URL) || 'ws://localhost:8080';

export interface RtEvent {
  type: string;
  tenant_id: number;
  ts: string;
  payload: Record<string, unknown>;
}

export type EventHandler = (event: RtEvent) => void;

export interface RtClientOptions {
  url?: string;
  mintToken?: () => Promise<string>;
  WebSocketImpl?: typeof WebSocket;
  /** Initial reconnect delay (ms). Doubles with each consecutive failure. */
  reconnectMinMs?: number;
  /** Cap on the reconnect delay. */
  reconnectMaxMs?: number;
}

/**
 * Stateful WebSocket client. Mints a 60s ws-token, opens the gateway, sends
 * the {type:"auth"} frame, fans incoming domain events out to subscribers,
 * auto-pongs server pings, and reconnects with exponential backoff after any
 * close.
 */
export class RtClient {
  private ws: WebSocket | null = null;
  private readonly handlers = new Set<EventHandler>();
  private reconnectAttempt = 0;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private stopped = false;
  private readonly opts: Required<RtClientOptions>;

  constructor(opts: RtClientOptions = {}) {
    this.opts = {
      url: opts.url ?? RT_URL,
      mintToken: opts.mintToken ?? (async () => (await wsToken()).token),
      WebSocketImpl: opts.WebSocketImpl ?? globalThis.WebSocket,
      reconnectMinMs: opts.reconnectMinMs ?? 1000,
      reconnectMaxMs: opts.reconnectMaxMs ?? 30_000,
    };
  }

  on(handler: EventHandler): () => void {
    this.handlers.add(handler);
    return () => {
      this.handlers.delete(handler);
    };
  }

  start(): void {
    this.stopped = false;
    void this.connect();
  }

  stop(): void {
    this.stopped = true;
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      try {
        this.ws.close();
      } catch {
        /* already closed */
      }
      this.ws = null;
    }
  }

  private async connect(): Promise<void> {
    let token: string;
    try {
      token = await this.opts.mintToken();
    } catch {
      this.scheduleReconnect();
      return;
    }
    if (this.stopped) return;

    const ws = new this.opts.WebSocketImpl(`${this.opts.url}/ws`);
    this.ws = ws;

    ws.onopen = () => {
      ws.send(JSON.stringify({ type: 'auth', token }));
    };
    ws.onmessage = (ev: MessageEvent) => {
      this.handleMessage(ev.data);
    };
    ws.onclose = () => {
      this.ws = null;
      if (!this.stopped) this.scheduleReconnect();
    };
    ws.onerror = () => {
      // Browsers fire close after error; let the close handler handle it.
    };
  }

  private handleMessage(raw: unknown): void {
    let msg: Record<string, unknown>;
    try {
      const text = typeof raw === 'string' ? raw : String(raw);
      const parsed = JSON.parse(text);
      if (!parsed || typeof parsed !== 'object') return;
      msg = parsed as Record<string, unknown>;
    } catch {
      return;
    }
    const type = msg.type;
    if (typeof type !== 'string') return;

    if (type === 'ping') {
      try {
        this.ws?.send(JSON.stringify({ type: 'pong' }));
      } catch {
        /* socket closing */
      }
      return;
    }
    if (type === 'hello') {
      this.reconnectAttempt = 0; // mark this connection healthy
      return;
    }

    const event = msg as unknown as RtEvent;
    for (const h of this.handlers) {
      try {
        h(event);
      } catch {
        // Subscriber errors must not break the dispatch loop.
      }
    }
  }

  private scheduleReconnect(): void {
    if (this.stopped) return;
    const delay = Math.min(
      this.opts.reconnectMaxMs,
      this.opts.reconnectMinMs * 2 ** this.reconnectAttempt,
    );
    this.reconnectAttempt += 1;
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      void this.connect();
    }, delay);
  }
}

/**
 * React hook: open one RtClient per AuthProvider mount and subscribe the
 * given handler to domain events. Tears down on unmount.
 */
export function useRealtimeEvents(handler: EventHandler, enabled = true): void {
  useEffect(() => {
    if (!enabled) return;
    const client = new RtClient();
    const off = client.on(handler);
    client.start();
    return () => {
      off();
      client.stop();
    };
  }, [handler, enabled]);
}
