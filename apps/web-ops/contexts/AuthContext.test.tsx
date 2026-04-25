import { act, render, renderHook, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { tokens } from '@/lib/api';
import { AuthProvider, useAuth } from './AuthContext';

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

describe('AuthContext', () => {
  beforeEach(() => {
    tokens.clear();
    vi.restoreAllMocks();
  });
  afterEach(() => {
    tokens.clear();
  });

  it('useAuth throws outside the provider', () => {
    const Probe = () => {
      useAuth();
      return null;
    };
    expect(() => render(<Probe />)).toThrowError(/AuthProvider/);
  });

  it('login updates user, logout clears it', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      jsonResponse(200, {
        access: 'A1',
        refresh: 'R1',
        user: { id: 1, email: 'a@x', role: 'admin', tenant_id: 1 },
      }),
    );

    const { result } = renderHook(() => useAuth(), { wrapper: AuthProvider });
    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      await result.current.login('a@x', 'p');
    });
    expect(result.current.user?.email).toBe('a@x');

    act(() => {
      result.current.logout();
    });
    expect(result.current.user).toBeNull();
    expect(tokens.getAccess()).toBeNull();
  });

  it('attempts refresh on mount when a refresh token exists', async () => {
    tokens.setRefresh('R1');
    const spy = vi.spyOn(globalThis, 'fetch');
    spy.mockResolvedValueOnce(jsonResponse(200, { access: 'A1' }));

    const Probe = () => {
      const { loading } = useAuth();
      return <div>{loading ? 'loading' : 'ready'}</div>;
    };
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );
    await waitFor(() => expect(screen.getByText('ready')).toBeInTheDocument());
    expect(spy).toHaveBeenCalled();
    expect(tokens.getAccess()).toBe('A1');
  });
});
