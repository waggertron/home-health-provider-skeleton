'use client';

import { Button } from '@heroui/react';
import { useMutation } from '@tanstack/react-query';
import { useState } from 'react';
import { ApiError, apiFetch } from '@/lib/api';

// Default starting point near LA Basin centroid; each press jitters within
// ~1km so the ops console map marker actually moves.
const DEFAULT_CENTER = { lat: 34.05, lon: -118.25 };

interface PingPayload {
  lat: number;
  lon: number;
  ts: string;
}

async function postPosition(payload: PingPayload): Promise<void> {
  const r = await apiFetch('/api/v1/positions/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!r.ok) {
    let detail = `HTTP ${r.status}`;
    try {
      const data = (await r.json()) as { detail?: string };
      if (data?.detail) detail = data.detail;
    } catch {
      /* ignore */
    }
    throw new ApiError(r.status, detail);
  }
}

function jitter(v: number, max = 0.01): number {
  return v + (Math.random() - 0.5) * max * 2;
}

export function PositionPinger() {
  const [last, setLast] = useState<PingPayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const ping = useMutation<void, ApiError, PingPayload>({
    mutationFn: postPosition,
  });

  function send() {
    setError(null);
    const base = last ?? { ...DEFAULT_CENTER, ts: '' };
    const payload: PingPayload = {
      lat: jitter(base.lat),
      lon: jitter(base.lon),
      ts: new Date().toISOString(),
    };
    ping.mutate(payload, {
      onSuccess: () => setLast(payload),
      onError: (err) => setError(err.message),
    });
  }

  return (
    <div className="space-y-2">
      <Button
        onClick={send}
        isDisabled={ping.isPending}
        aria-label="Send GPS ping"
        className="w-full"
      >
        {ping.isPending ? 'Sending…' : 'Send GPS'}
      </Button>
      {last && (
        <p className="text-xs opacity-60" data-testid="last-ping">
          Last: {last.lat.toFixed(4)}, {last.lon.toFixed(4)}
        </p>
      )}
      {error && (
        <p role="alert" className="text-xs text-red-400">
          {error}
        </p>
      )}
    </div>
  );
}
