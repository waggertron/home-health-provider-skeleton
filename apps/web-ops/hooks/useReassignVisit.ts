'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { ApiError, apiFetch } from '@/lib/api';
import { VISITS_KEY, type Visit } from './useTodayBoard';

interface ReassignVars {
  visitId: number;
  clinicianId: number;
}

interface MutationContext {
  snapshot: Visit[] | undefined;
}

async function postAssign(vars: ReassignVars): Promise<Visit> {
  const r = await apiFetch(`/api/v1/visits/${vars.visitId}/assign/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ clinician_id: vars.clinicianId }),
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

export function useReassignVisit() {
  const qc = useQueryClient();
  return useMutation<Visit, ApiError, ReassignVars, MutationContext>({
    mutationFn: postAssign,
    onMutate: async ({ visitId, clinicianId }) => {
      await qc.cancelQueries({ queryKey: VISITS_KEY });
      const snapshot = qc.getQueryData<Visit[]>(VISITS_KEY);
      qc.setQueryData<Visit[]>(VISITS_KEY, (current) =>
        current?.map((v) =>
          v.id === visitId ? { ...v, clinician: clinicianId, status: 'assigned' } : v,
        ),
      );
      return { snapshot };
    },
    onError: (_error, _vars, context) => {
      if (context?.snapshot) {
        qc.setQueryData<Visit[]>(VISITS_KEY, context.snapshot);
      }
    },
    onSuccess: (updated) => {
      qc.setQueryData<Visit[]>(VISITS_KEY, (current) =>
        current?.map((v) => (v.id === updated.id ? updated : v)),
      );
    },
  });
}
