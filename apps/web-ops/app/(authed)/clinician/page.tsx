'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@heroui/react';
import { useAuth } from '@/contexts/AuthContext';

export default function ClinicianPage() {
  const { user, logout } = useAuth();
  return (
    <main className="min-h-screen p-6 max-w-md mx-auto space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>My route · {user?.email}</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm opacity-70">Tenant {user?.tenant_id} · role {user?.role}</p>
          <p className="text-sm mt-2">Today's visits land in T4. Position pinger lands in T5.</p>
          <button
            type="button"
            onClick={logout}
            className="mt-4 text-sm text-blue-400 underline"
          >
            Sign out
          </button>
        </CardContent>
      </Card>
    </main>
  );
}
