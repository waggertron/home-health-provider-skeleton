import http from 'node:http';
import Redis from 'ioredis';
import { WebSocketServer, type WebSocket } from 'ws';
import { verifyToken } from './auth.js';
import { SubscriberManager } from './redis.js';

const DEFAULT_PORT = 8080;

export interface RtServer {
  httpServer: http.Server;
  wss: WebSocketServer;
  subs: SubscriberManager;
  redis: Redis;
  close: () => Promise<void>;
}

export interface RtServerOptions {
  port?: number;
  redisUrl?: string;
  signingKey: string;
}

export function createServer(opts: RtServerOptions): RtServer {
  const redis = new Redis(opts.redisUrl ?? 'redis://cache-redis:6379/0');
  const subs = new SubscriberManager(redis);

  const httpServer = http.createServer((req, res) => {
    if (req.url === '/healthz') {
      res.writeHead(200, { 'Content-Type': 'text/plain' });
      res.end('ok');
      return;
    }
    res.writeHead(404).end();
  });

  const wss = new WebSocketServer({ server: httpServer, path: '/ws' });

  wss.on('connection', (ws) => {
    attachConnection(ws, subs, opts.signingKey);
  });

  return {
    httpServer,
    wss,
    subs,
    redis,
    close: async () => {
      await new Promise<void>((r) => wss.close(() => r()));
      await new Promise<void>((r) => httpServer.close(() => r()));
      await redis.quit();
    },
  };
}

/** One connection's lifecycle. Exported for tests. */
export function attachConnection(
  ws: WebSocket,
  subs: SubscriberManager,
  signingKey: string,
): void {
  let authed = false;
  let channel: string | null = null;
  const handler = (message: string) => ws.send(message);

  ws.on('message', async (raw) => {
    let msg: { type?: unknown; token?: unknown };
    try {
      msg = JSON.parse(raw.toString());
    } catch {
      return;
    }
    if (!authed && msg.type === 'auth' && typeof msg.token === 'string') {
      const claims = verifyToken(msg.token, signingKey);
      if (!claims) {
        ws.close(4401, 'auth failed');
        return;
      }
      authed = true;
      channel = `tenant:${claims.tenantId}:events`;
      await subs.subscribe(channel, handler);
      ws.send(JSON.stringify({ type: 'hello', tenant_id: claims.tenantId }));
    }
  });

  ws.on('close', () => {
    if (channel) void subs.unsubscribe(channel, handler);
  });
}

const entry = process.argv[1];
const isDirectRun = entry && import.meta.url === `file://${entry}`;
if (isDirectRun) {
  const port = Number(process.env.PORT ?? DEFAULT_PORT);
  const signingKey = process.env.JWT_SIGNING_KEY ?? '';
  if (!signingKey) {
    console.error('JWT_SIGNING_KEY is required');
    process.exit(1);
  }
  const { httpServer } = createServer({
    port,
    redisUrl: process.env.REDIS_URL,
    signingKey,
  });
  httpServer.listen(port, () => {
    console.log(`rt-node listening on :${port}`);
  });
}
