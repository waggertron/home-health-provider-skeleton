'use client';

import { Button } from '@heroui/react';
import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { useReassignVisit } from '@/hooks/useReassignVisit';
import type { Clinician, Visit } from '@/hooks/useTodayBoard';
import { CREDENTIAL_RANK, canServe } from '@/lib/credentials';

interface ReassignModalProps {
  visit: Visit;
  clinicians: Clinician[];
  open: boolean;
  onClose: () => void;
}

export function ReassignModal({ visit, clinicians, open, onClose }: ReassignModalProps) {
  const reassign = useReassignVisit();
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const eligible = useMemo(() => {
    return clinicians
      .filter((c) => canServe(c.credential, visit.required_skill))
      .sort((a, b) => {
        const rb = CREDENTIAL_RANK[b.credential] ?? 0;
        const ra = CREDENTIAL_RANK[a.credential] ?? 0;
        if (rb !== ra) return rb - ra;
        return a.id - b.id;
      });
  }, [clinicians, visit.required_skill]);

  // Reset transient state whenever the dialog re-opens.
  // The mutation object's identity changes per render — using a ref keeps
  // the deps array narrow enough to avoid an effect-loop.
  const reassignRef = useRef(reassign);
  reassignRef.current = reassign;
  useEffect(() => {
    if (open) {
      reassignRef.current.reset();
      setErrorMsg(null);
    }
  }, [open]);

  if (!open) return null;

  function pick(clinicianId: number) {
    setErrorMsg(null);
    reassign.mutate(
      { visitId: visit.id, clinicianId },
      {
        onSuccess: () => onClose(),
        onError: (err) => setErrorMsg(err.message),
      },
    );
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={`Reassign visit ${visit.id}`}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
    >
      <div className="bg-slate-900 border border-slate-700 rounded-lg w-full max-w-md p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Reassign visit #{visit.id}</h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="text-sm opacity-70 hover:opacity-100"
          >
            ✕
          </button>
        </div>
        <p className="text-sm opacity-70">
          Required skill: <span className="font-mono">{visit.required_skill}</span>
        </p>
        {eligible.length === 0 ? (
          <p className="text-sm text-amber-400">
            No clinicians with the required credential are on duty.
          </p>
        ) : (
          <ul className="divide-y divide-slate-800" data-testid="clinician-list">
            {eligible.map((c) => (
              <Row key={c.id} clinician={c} onPick={() => pick(c.id)} disabled={reassign.isPending} />
            ))}
          </ul>
        )}
        {errorMsg && (
          <p role="alert" className="text-sm text-red-400">
            {errorMsg}
          </p>
        )}
      </div>
    </div>
  );
}

function Row({
  clinician,
  onPick,
  disabled,
}: {
  clinician: Clinician;
  onPick: () => void;
  disabled: boolean;
}): ReactNode {
  return (
    <li className="flex items-center justify-between py-2">
      <div className="text-sm">
        <span className="font-medium">Clinician #{clinician.id}</span>
        <span className="ml-2 opacity-70">{clinician.credential}</span>
      </div>
      <Button size="sm" onClick={onPick} isDisabled={disabled} aria-label={`Assign to ${clinician.id}`}>
        Assign
      </Button>
    </li>
  );
}
