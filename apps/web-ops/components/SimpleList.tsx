'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@heroui/react';
import { useQuery } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { apiFetch } from '@/lib/api';

interface SimpleListProps<T extends { id: number }> {
  title: string;
  queryKey: readonly unknown[];
  path: string;
  columns: { header: string; render: (row: T) => ReactNode }[];
  testId?: string;
}

async function fetchList<T>(path: string): Promise<T[]> {
  const r = await apiFetch(path);
  if (!r.ok) throw new Error(`${path}: ${r.status}`);
  const data = (await r.json()) as T[] | { results: T[] };
  return Array.isArray(data) ? data : data.results;
}

export function SimpleList<T extends { id: number }>({
  title,
  queryKey,
  path,
  columns,
  testId,
}: SimpleListProps<T>) {
  const q = useQuery({ queryKey, queryFn: () => fetchList<T>(path) });

  return (
    <main className="min-h-screen p-8">
      <Card>
        <CardHeader>
          <CardTitle>{title}</CardTitle>
        </CardHeader>
        <CardContent>
          {q.isLoading ? (
            <p className="text-sm opacity-70">Loading…</p>
          ) : q.error ? (
            <p role="alert" className="text-sm text-red-400">
              Failed to load {title.toLowerCase()}.
            </p>
          ) : (
            <table className="w-full text-sm" data-testid={testId ?? 'simple-list'}>
              <thead>
                <tr className="text-left opacity-70">
                  {columns.map((c) => (
                    <th key={c.header} className="py-2 pr-4">
                      {c.header}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {(q.data ?? []).map((row) => (
                  <tr key={row.id} className="border-t border-slate-800">
                    {columns.map((c) => (
                      <td key={c.header} className="py-2 pr-4">
                        {c.render(row)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>
    </main>
  );
}
