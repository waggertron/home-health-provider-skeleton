'use client';

import { Button } from '@heroui/react';
import { useState } from 'react';
import { apiFetch } from '@/lib/api';
import { useTodayBoard, type Visit } from '@/hooks/useTodayBoard';
import { VisitCard } from './VisitCard';

const STATUSES = ['all', 'scheduled', 'assigned', 'en_route', 'on_site', 'completed'] as const;

interface TodayBoardProps {
  tenantId: number | undefined;
}

export function TodayBoard({ tenantId }: TodayBoardProps) {
  const { visits, clinicians } = useTodayBoard(tenantId);
  const [statusFilter, setStatusFilter] = useState<(typeof STATUSES)[number]>('all');
  const [optimizing, setOptimizing] = useState(false);

  async function onOptimize() {
    const today = new Date().toISOString().slice(0, 10);
    setOptimizing(true);
    try {
      await apiFetch(`/api/v1/schedule/${today}/optimize`, { method: 'POST' });
    } finally {
      // The schedule.optimized realtime frame will trigger a cache refresh.
      setOptimizing(false);
    }
  }

  const rows: Visit[] = visits.data ?? [];
  const filtered = statusFilter === 'all' ? rows : rows.filter((v) => v.status === statusFilter);

  return (
    <main className="min-h-screen p-8 space-y-6">
      <header className="flex flex-wrap items-center gap-4">
        <h1 className="text-xl font-semibold">Today · {filtered.length} of {rows.length} visits</h1>
        <div className="flex items-center gap-2">
          <label htmlFor="status-filter" className="text-sm opacity-70">
            Status
          </label>
          <select
            id="status-filter"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as (typeof STATUSES)[number])}
            className="bg-slate-900 text-slate-100 border border-slate-700 rounded px-2 py-1 text-sm"
          >
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>
        <Button onClick={onOptimize} isDisabled={optimizing} aria-label="Optimize today's schedule">
          {optimizing ? 'Optimizing…' : 'Optimize Day'}
        </Button>
        <span className="text-xs opacity-50">{(clinicians.data ?? []).length} clinicians on duty</span>
      </header>

      {visits.isLoading ? (
        <p className="text-sm opacity-70">Loading visits…</p>
      ) : visits.error ? (
        <p role="alert" className="text-sm text-red-400">
          Failed to load visits.
        </p>
      ) : (
        <ul className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="visit-grid">
          {filtered.map((v) => (
            <li key={v.id}>
              <VisitCard visit={v} />
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
