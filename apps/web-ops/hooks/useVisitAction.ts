'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { ApiError, apiFetch } from '@/lib/api';
import { MY_VISITS_KEY } from './useMyRoute';
import type { Visit } from './useTodayBoard';

export type VisitAction = 'check-in' | 'check-out' | 'cancel';

interface ActionVars {
  visitId: number;
  action: VisitAction;
  body?: Record<string, unknown>;
  /** Optimistic next status; if set, patches the row in MY_VISITS_KEY. */
  optimisticStatus?: string;
}

interface MutationContext {
  snapshot: Visit[] | undefined;
}

async function postAction(vars: ActionVars): Promise<Visit> {
  const r = await apiFetch(`/api/v1/visits/${vars.visitId}/${vars.action}/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(vars.body ?? {}),
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
  return (await r.json()) as Visit;
}

export function useVisitAction() {
  const qc = useQueryClient();
  return useMutation<Visit, ApiError, ActionVars, MutationContext>({
    mutationFn: postAction,
    onMutate: async ({ visitId, optimisticStatus }) => {
      await qc.cancelQueries({ queryKey: MY_VISITS_KEY });
      const snapshot = qc.getQueryData<Visit[]>(MY_VISITS_KEY);
      if (optimisticStatus) {
        qc.setQueryData<Visit[]>(MY_VISITS_KEY, (current) =>
          current?.map((v) => (v.id === visitId ? { ...v, status: optimisticStatus } : v)),
        );
      }
      return { snapshot };
    },
    onError: (_error, _vars, context) => {
      if (context?.snapshot) {
        qc.setQueryData<Visit[]>(MY_VISITS_KEY, context.snapshot);
      }
    },
    onSuccess: (updated) => {
      qc.setQueryData<Visit[]>(MY_VISITS_KEY, (current) =>
        current?.map((v) => (v.id === updated.id ? updated : v)),
      );
    },
  });
}
