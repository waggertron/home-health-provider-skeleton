'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@heroui/react';
import { useAuth } from '@/contexts/AuthContext';

export default function TodayPage() {
  const { user, logout } = useAuth();
  return (
    <main className="min-h-screen p-8">
      <Card className="max-w-2xl mx-auto">
        <CardHeader>
          <CardTitle>Today · {user?.email}</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm">Phase 5 board lands in T6.</p>
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
