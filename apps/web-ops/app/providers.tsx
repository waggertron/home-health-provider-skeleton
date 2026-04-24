'use client';

import { I18nProvider, ToastProvider } from '@heroui/react';
import type { ReactNode } from 'react';

export function Providers({ children }: { children: ReactNode }) {
  return (
    <I18nProvider locale="en-US">
      <ToastProvider>{children}</ToastProvider>
    </I18nProvider>
  );
}
