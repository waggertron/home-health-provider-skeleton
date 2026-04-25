import { I18nProvider } from '@heroui/react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { AuthProvider } from '@/contexts/AuthContext';
import { tokens } from '@/lib/api';
import LoginPage from './page';

const pushMock = vi.fn();
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: pushMock, replace: vi.fn() }),
}));

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

function renderLogin() {
  return render(
    <I18nProvider locale="en-US">
      <AuthProvider>
        <LoginPage />
      </AuthProvider>
    </I18nProvider>,
  );
}

describe('<LoginPage />', () => {
  beforeEach(() => {
    tokens.clear();
    pushMock.mockClear();
    vi.restoreAllMocks();
  });
  afterEach(() => tokens.clear());

  it('happy path: submits and redirects to /today', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      jsonResponse(200, {
        access: 'A1',
        refresh: 'R1',
        user: { id: 1, email: 'admin@x.demo', role: 'admin', tenant_id: 1 },
      }),
    );
    renderLogin();
    const user = userEvent.setup();
    await user.type(screen.getByLabelText(/email/i), 'admin@x.demo');
    await user.type(screen.getByLabelText(/password/i), 'demo1234');
    await user.click(screen.getByRole('button', { name: /sign in/i }));
    await waitFor(() => expect(pushMock).toHaveBeenCalledWith('/today'));
  });

  it('shows the error from the API on bad credentials', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      jsonResponse(401, { detail: 'Invalid credentials' }),
    );
    renderLogin();
    const user = userEvent.setup();
    await user.type(screen.getByLabelText(/email/i), 'admin@x.demo');
    await user.type(screen.getByLabelText(/password/i), 'wrong');
    await user.click(screen.getByRole('button', { name: /sign in/i }));
    expect(await screen.findByRole('alert')).toHaveTextContent(/Invalid credentials/i);
    expect(pushMock).not.toHaveBeenCalled();
  });
});
