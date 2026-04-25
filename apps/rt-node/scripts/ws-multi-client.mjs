#!/usr/bin/env node
/* eslint-disable no-console */
/**
 * Wait for several event types on a single WS connection.
 *
 *   node scripts/ws-multi-client.mjs <ws-url> <token> <type1,type2,...> [timeout-ms]
 *
 * Exits 0 once at least one frame of each expected type has arrived, exits 1
 * on timeout. Echoes pongs back to the server so the heartbeat stays happy.
 */
import WebSocket from 'ws';

const [url, token, typesArg, timeoutArg = '20000'] = process.argv.slice(2);
const expectedTypes = (typesArg ?? '').split(',').filter(Boolean);
const timeoutMs = Number(timeoutArg);

if (!url || !token || expectedTypes.length === 0) {
  console.error(
    'usage: ws-multi-client.mjs <ws-url> <token> <type1[,type2,...]> [timeout-ms]',
  );
  process.exit(2);
}

const ws = new WebSocket(url);
const remaining = new Set(expectedTypes);

const timer = setTimeout(() => {
  console.error(
    `timeout: still waiting on [${[...remaining].join(', ')}] after ${timeoutMs}ms`,
  );
  ws.terminate();
  process.exit(1);
}, timeoutMs);

ws.on('open', () => {
  ws.send(JSON.stringify({ type: 'auth', token }));
});

ws.on('message', (raw) => {
  let msg;
  try {
    msg = JSON.parse(raw.toString());
  } catch {
    return;
  }
  if (msg.type === 'ping') {
    ws.send(JSON.stringify({ type: 'pong' }));
    return;
  }
  if (msg.type === 'hello') {
    console.log('-- authenticated, tenant', msg.tenant_id);
    return;
  }
  if (remaining.has(msg.type)) {
    console.log('<-', msg.type);
    remaining.delete(msg.type);
    if (remaining.size === 0) {
      clearTimeout(timer);
      ws.close();
    }
  }
});

ws.on('close', () => {
  if (remaining.size === 0) process.exit(0);
});

ws.on('error', (err) => {
  console.error('ws error:', err.message);
  clearTimeout(timer);
  process.exit(1);
});
