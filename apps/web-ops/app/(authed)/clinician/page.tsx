'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@heroui/react';
import { MyRoute } from '@/components/MyRoute';
import { PositionPinger } from '@/components/PositionPinger';
import { useAuth } from '@/contexts/AuthContext';

export default function ClinicianPage() {
  const { user, logout } = useAuth();
  return (
    <main className="min-h-screen p-6 max-w-md mx-auto space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>My route · {user?.email}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm opacity-70">
            Tenant {user?.tenant_id} · clinician #{user?.clinician_id ?? '—'}
          </p>
          <PositionPinger />
          <button
            type="button"
            onClick={logout}
            className="text-sm text-blue-400 underline"
          >
            Sign out
          </button>
        </CardContent>
      </Card>
      <MyRoute clinicianId={user?.clinician_id ?? undefined} tenantId={user?.tenant_id} />
    </main>
  );
}
