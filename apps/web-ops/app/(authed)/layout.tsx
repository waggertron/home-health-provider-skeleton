'use client';

import { usePathname, useRouter } from 'next/navigation';
import { type ReactNode, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';

export default function AuthedLayout({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (loading) return;
    if (!user) {
      router.replace('/login');
      return;
    }
    const onClinician = pathname?.startsWith('/clinician') ?? false;
    if (user.role === 'clinician' && !onClinician) {
      router.replace('/clinician');
    } else if (user.role !== 'clinician' && onClinician) {
      router.replace('/today');
    }
  }, [loading, user, pathname, router]);

  if (loading || !user) {
    return <p className="p-8 text-sm">Loading…</p>;
  }
  return <>{children}</>;
}
