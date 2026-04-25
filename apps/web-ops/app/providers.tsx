'use client';

import { I18nProvider, ToastProvider } from '@heroui/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState, type ReactNode } from 'react';
import { AuthProvider } from '@/contexts/AuthContext';

export function Providers({ children }: { children: ReactNode }) {
  // One QueryClient per browser session. useState pins it across re-renders.
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: { staleTime: 30_000, refetchOnWindowFocus: false },
        },
      }),
  );

  return (
    <I18nProvider locale="en-US">
      <ToastProvider>
        <QueryClientProvider client={queryClient}>
          <AuthProvider>{children}</AuthProvider>
        </QueryClientProvider>
      </ToastProvider>
    </I18nProvider>
  );
}
