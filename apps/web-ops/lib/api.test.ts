import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError, apiFetch, login, logout, refresh, tokens, wsToken } from './api';

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

describe('lib/api', () => {
  beforeEach(() => {
    tokens.clear();
    vi.restoreAllMocks();
  });
  afterEach(() => {
    tokens.clear();
  });

  describe('login', () => {
    it('stores access + refresh tokens on success', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        jsonResponse(200, {
          access: 'A1',
          refresh: 'R1',
          user: { id: 1, email: 'a@x', role: 'admin', tenant_id: 1 },
        }),
      );
      const r = await login('a@x', 'p');
      expect(r.access).toBe('A1');
      expect(tokens.getAccess()).toBe('A1');
      expect(tokens.getRefresh()).toBe('R1');
    });

    it('throws ApiError on 401', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        jsonResponse(401, { detail: 'Invalid credentials' }),
      );
      await expect(login('a@x', 'wrong')).rejects.toBeInstanceOf(ApiError);
    });
  });

  describe('refresh', () => {
    it('updates access token on success', async () => {
      tokens.setRefresh('R1');
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(jsonResponse(200, { access: 'A2' }));
      const access = await refresh();
      expect(access).toBe('A2');
      expect(tokens.getAccess()).toBe('A2');
    });

    it('clears tokens on failure', async () => {
      tokens.setAccess('A1');
      tokens.setRefresh('R1');
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(jsonResponse(401, { detail: 'bad' }));
      await expect(refresh()).rejects.toBeInstanceOf(ApiError);
      expect(tokens.getAccess()).toBeNull();
      expect(tokens.getRefresh()).toBeNull();
    });

    it('throws when no refresh token is present', async () => {
      await expect(refresh()).rejects.toBeInstanceOf(ApiError);
    });
  });

  describe('apiFetch', () => {
    it('attaches Bearer header on the first try', async () => {
      tokens.setAccess('A1');
      const spy = vi
        .spyOn(globalThis, 'fetch')
        .mockResolvedValueOnce(jsonResponse(200, { ok: true }));
      await apiFetch('/api/v1/visits/');
      const init = spy.mock.calls[0][1];
      const headers = new Headers(init?.headers);
      expect(headers.get('authorization')).toBe('Bearer A1');
    });

    it('retries once with a fresh access token after a 401', async () => {
      tokens.setAccess('A1');
      tokens.setRefresh('R1');
      const spy = vi.spyOn(globalThis, 'fetch');
      spy.mockResolvedValueOnce(jsonResponse(401, { detail: 'expired' })); // first call
      spy.mockResolvedValueOnce(jsonResponse(200, { access: 'A2' })); // refresh
      spy.mockResolvedValueOnce(jsonResponse(200, { ok: true })); // retry
      const r = await apiFetch('/api/v1/visits/');
      expect(r.status).toBe(200);
      expect(spy).toHaveBeenCalledTimes(3);
      expect(tokens.getAccess()).toBe('A2');
    });

    it('returns the original 401 when refresh fails', async () => {
      tokens.setAccess('A1');
      tokens.setRefresh('R1');
      const spy = vi.spyOn(globalThis, 'fetch');
      spy.mockResolvedValueOnce(jsonResponse(401, { detail: 'expired' }));
      spy.mockResolvedValueOnce(jsonResponse(401, { detail: 'refresh expired' }));
      const r = await apiFetch('/api/v1/visits/');
      expect(r.status).toBe(401);
      expect(tokens.getAccess()).toBeNull();
    });

    it('skips refresh when no refresh token is present', async () => {
      tokens.setAccess('A1');
      const spy = vi.spyOn(globalThis, 'fetch');
      spy.mockResolvedValueOnce(jsonResponse(401, { detail: 'expired' }));
      const r = await apiFetch('/api/v1/visits/');
      expect(r.status).toBe(401);
      expect(spy).toHaveBeenCalledTimes(1);
    });
  });

  describe('wsToken', () => {
    it('returns the token + expires_in payload', async () => {
      tokens.setAccess('A1');
      vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
        jsonResponse(200, { token: 'WS', expires_in: 60 }),
      );
      const r = await wsToken();
      expect(r).toEqual({ token: 'WS', expires_in: 60 });
    });
  });

  describe('logout', () => {
    it('clears in-memory access + localStorage refresh', () => {
      tokens.setAccess('A1');
      tokens.setRefresh('R1');
      logout();
      expect(tokens.getAccess()).toBeNull();
      expect(tokens.getRefresh()).toBeNull();
    });
  });
});
