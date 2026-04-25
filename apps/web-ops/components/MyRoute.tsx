'use client';

import { Badge, Button, Card, CardContent, CardHeader } from '@heroui/react';
import { useState } from 'react';
import { useMyRoute } from '@/hooks/useMyRoute';
import { useVisitAction, type VisitAction } from '@/hooks/useVisitAction';
import type { Visit } from '@/hooks/useTodayBoard';

const STATUS_COLOR: Record<string, string> = {
  scheduled: 'bg-slate-700 text-slate-100',
  assigned: 'bg-blue-700 text-blue-100',
  en_route: 'bg-amber-700 text-amber-100',
  on_site: 'bg-amber-500 text-amber-950',
  completed: 'bg-emerald-700 text-emerald-100',
  cancelled: 'bg-rose-900 text-rose-200',
  missed: 'bg-rose-700 text-rose-100',
};

interface NextActionMeta {
  action: VisitAction;
  label: string;
  next: string;
  body?: Record<string, unknown>;
}

function nextAction(visit: Visit): NextActionMeta | null {
  switch (visit.status) {
    case 'assigned':
    case 'en_route':
      return { action: 'check-in', label: 'Check In', next: 'on_site', body: { lat: 0, lon: 0 } };
    case 'on_site':
      return { action: 'check-out', label: 'Check Out', next: 'completed' };
    default:
      return null;
  }
}

interface MyRouteProps {
  clinicianId: number | undefined;
  tenantId: number | undefined;
}

export function MyRoute({ clinicianId, tenantId }: MyRouteProps) {
  const visits = useMyRoute(clinicianId, tenantId);
  const action = useVisitAction();
  const [errorByVisit, setErrorByVisit] = useState<Record<number, string>>({});

  const rows = visits.data ?? [];

  if (visits.isLoading) {
    return <p className="text-sm opacity-70">Loading your route…</p>;
  }
  if (visits.error) {
    return (
      <p role="alert" className="text-sm text-red-400">
        Failed to load your route.
      </p>
    );
  }
  if (rows.length === 0) {
    return <p className="text-sm opacity-70">No visits assigned today.</p>;
  }

  return (
    <ul className="space-y-3" data-testid="my-route">
      {rows.map((v) => (
        <VisitRow
          key={v.id}
          testId={`my-visit-${v.id}`}
          visit={v}
          isPending={action.isPending && action.variables?.visitId === v.id}
          error={errorByVisit[v.id]}
          onAct={(meta) => {
            setErrorByVisit((prev) => ({ ...prev, [v.id]: '' }));
            action.mutate(
              {
                visitId: v.id,
                action: meta.action,
                body: meta.body,
                optimisticStatus: meta.next,
              },
              {
                onError: (err) =>
                  setErrorByVisit((prev) => ({ ...prev, [v.id]: err.message })),
              },
            );
          }}
        />
      ))}
    </ul>
  );
}

function VisitRow({
  visit,
  isPending,
  error,
  onAct,
  testId,
}: {
  visit: Visit;
  isPending: boolean;
  error?: string;
  onAct: (meta: NextActionMeta) => void;
  testId?: string;
}) {
  const next = nextAction(visit);
  const start = new Date(visit.window_start);
  return (
    <li data-testid={testId}>
      <Card>
        <CardHeader className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-xs uppercase opacity-70">
              {visit.ordering_seq !== null ? `#${visit.ordering_seq + 1}` : 'unordered'}
            </span>
            <Badge className={STATUS_COLOR[visit.status] ?? 'bg-slate-700 text-slate-100'}>
              {visit.status.replace('_', ' ')}
            </Badge>
          </div>
          <span className="text-xs opacity-70">
            {start.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}
          </span>
        </CardHeader>
        <CardContent>
          <p className="text-sm">Patient #{visit.patient} · skill {visit.required_skill}</p>
          {next && (
            <Button
              className="mt-3 w-full"
              onClick={() => onAct(next)}
              isDisabled={isPending}
              aria-label={`${next.label} visit ${visit.id}`}
            >
              {isPending ? '…' : next.label}
            </Button>
          )}
          {error && (
            <p role="alert" className="text-xs text-red-400 mt-2">
              {error}
            </p>
          )}
        </CardContent>
      </Card>
    </li>
  );
}
