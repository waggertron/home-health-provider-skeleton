import { I18nProvider } from '@heroui/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { tokens } from '@/lib/api';
import { SimpleList } from './SimpleList';

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

interface Row {
  id: number;
  name: string;
  credential: string;
}

const ROWS: Row[] = [
  { id: 1, name: 'Alice', credential: 'RN' },
  { id: 2, name: 'Bob', credential: 'MA' },
];

function renderList(status: number = 200, body: unknown = ROWS) {
  vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(jsonResponse(status, body));
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <I18nProvider locale="en-US">
      <QueryClientProvider client={qc}>
        <SimpleList<Row>
          title="Test"
          queryKey={['simple-list-test']}
          path="/api/v1/test/"
          columns={[
            { header: 'ID', render: (r) => r.id },
            { header: 'Name', render: (r) => r.name },
            { header: 'Credential', render: (r) => r.credential },
          ]}
        />
      </QueryClientProvider>
    </I18nProvider>,
  );
}

describe('<SimpleList />', () => {
  beforeEach(() => {
    tokens.setAccess('A1');
  });
  afterEach(() => {
    vi.restoreAllMocks();
    tokens.clear();
  });

  it('renders one row per record', async () => {
    renderList();
    await waitFor(() => screen.getByText('Alice'));
    expect(screen.getByText('Alice')).toBeInTheDocument();
    expect(screen.getByText('Bob')).toBeInTheDocument();
  });

  it('renders three column headers from the columns prop', async () => {
    renderList();
    await waitFor(() => screen.getByText('Alice'));
    expect(screen.getAllByRole('columnheader').length).toBe(3);
  });

  it('renders an alert on a non-2xx response', async () => {
    renderList(500, { detail: 'oops' });
    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument());
  });

  it('handles a paginated {results: [...]} response shape', async () => {
    renderList(200, { count: 2, results: ROWS });
    await waitFor(() => screen.getByText('Alice'));
    expect(screen.getByText('Bob')).toBeInTheDocument();
  });
});
