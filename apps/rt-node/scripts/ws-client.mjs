#!/usr/bin/env node
/* eslint-disable no-console */
/**
 * Minimal WS client used by ops/ws-smoke.sh.
 *
 *   node scripts/ws-client.mjs <ws-url> <token> [expected-type] [timeout-ms]
 *
 * Connects, sends {type:"auth", token}, then waits for the first frame of the
 * expected type (default: schedule.optimized). Exits 0 on receipt, 1 on
 * timeout or error.
 */
import WebSocket from 'ws';

const [url, token, expectedType = 'schedule.optimized', timeoutArg = '5000'] = process.argv.slice(2);
const timeoutMs = Number(timeoutArg);

if (!url || !token) {
  console.error('usage: ws-client.mjs <ws-url> <token> [expected-type] [timeout-ms]');
  process.exit(2);
}

const ws = new WebSocket(url);
let received = false;

const timer = setTimeout(() => {
  console.error(`timeout: no ${expectedType} frame within ${timeoutMs}ms`);
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
  console.log('<-', msg.type);
  if (msg.type === expectedType) {
    received = true;
    clearTimeout(timer);
    ws.close();
  }
});

ws.on('close', () => {
  if (received) process.exit(0);
});

ws.on('error', (err) => {
  console.error('ws error:', err.message);
  clearTimeout(timer);
  process.exit(1);
});
