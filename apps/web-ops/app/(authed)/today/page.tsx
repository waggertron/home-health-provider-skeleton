'use client';

import { TodayBoard } from '@/components/TodayBoard';
import { useAuth } from '@/contexts/AuthContext';

export default function TodayPage() {
  const { user } = useAuth();
  return <TodayBoard tenantId={user?.tenant_id} />;
}
