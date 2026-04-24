import type { WebSocket } from 'ws';

export interface HeartbeatOpts {
  ws: WebSocket;
  /** Send {type:"ping"} every intervalMs. */
  intervalMs: number;
  /** Terminate the socket if no pong arrives within timeoutMs. */
  timeoutMs: number;
}

/**
 * Application-level heartbeat. Sends JSON ping frames every intervalMs
 * and terminates the socket when the gap since the last pong exceeds
 * timeoutMs. Clients echo {type:"pong"} on receipt; the message-handler
 * in attachConnection calls markPong().
 */
export class Heartbeat {
  private lastPong: number;
  private timer: ReturnType<typeof setInterval> | null = null;

  constructor(private readonly opts: HeartbeatOpts) {
    this.lastPong = Date.now();
  }

  start(): void {
    if (this.timer) return;
    this.timer = setInterval(() => this.tick(), this.opts.intervalMs);
  }

  stop(): void {
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = null;
    }
  }

  markPong(): void {
    this.lastPong = Date.now();
  }

  private tick(): void {
    const elapsed = Date.now() - this.lastPong;
    if (elapsed > this.opts.timeoutMs) {
      this.opts.ws.terminate();
      this.stop();
      return;
    }
    try {
      this.opts.ws.send(JSON.stringify({ type: 'ping' }));
    } catch {
      // Closed mid-send — let the close handler tear down.
    }
  }
}
