'use client';

import { OpsMap } from '@/components/OpsMap';
import { TodayBoard } from '@/components/TodayBoard';
import { useAuth } from '@/contexts/AuthContext';

export default function TodayPage() {
  const { user } = useAuth();
  return (
    <div className="space-y-6 p-8">
      <OpsMap tenantId={user?.tenant_id} />
      <TodayBoard tenantId={user?.tenant_id} />
    </div>
  );
}
