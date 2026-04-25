'use client';

import { I18nProvider, ToastProvider } from '@heroui/react';
import type { ReactNode } from 'react';
import { AuthProvider } from '@/contexts/AuthContext';

export function Providers({ children }: { children: ReactNode }) {
  return (
    <I18nProvider locale="en-US">
      <ToastProvider>
        <AuthProvider>{children}</AuthProvider>
      </ToastProvider>
    </I18nProvider>
  );
}
