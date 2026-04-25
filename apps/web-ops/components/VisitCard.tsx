'use client';

import { Badge, Card, CardContent, CardHeader } from '@heroui/react';
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

interface VisitCardProps {
  visit: Visit;
  testId?: string;
}

export function VisitCard({ visit, testId }: VisitCardProps) {
  const start = new Date(visit.window_start);
  const startLabel = start.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
  return (
    <Card data-testid={testId ?? `visit-${visit.id}`}>
      <CardHeader className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xs uppercase opacity-70">Visit #{visit.id}</span>
          <Badge className={STATUS_COLOR[visit.status] ?? 'bg-slate-700 text-slate-100'}>
            {visit.status.replace('_', ' ')}
          </Badge>
        </div>
        <span className="text-xs opacity-70">{startLabel}</span>
      </CardHeader>
      <CardContent>
        <div className="text-sm space-y-1">
          <div>Skill: {visit.required_skill}</div>
          <div>Clinician: {visit.clinician ?? 'unassigned'}</div>
        </div>
      </CardContent>
    </Card>
  );
}
