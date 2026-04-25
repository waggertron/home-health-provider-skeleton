/**
 * API client for the Django backend.
 *
 * Holds the access token in memory and the refresh token in localStorage.
 * apiFetch transparently retries on 401 by minting a fresh access token via
 * the refresh endpoint, then replaying the original request once.
 */

const API_URL =
  (typeof process !== 'undefined' && process.env.NEXT_PUBLIC_API_URL) || 'http://localhost:8000';

export interface UserInfo {
  id: number;
  email: string;
  role: 'admin' | 'scheduler' | 'clinician';
  tenant_id?: number;
}

export interface LoginResponse {
  access: string;
  refresh: string;
  user: UserInfo;
}

export interface WsTokenResponse {
  token: string;
  expires_in: number;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

class TokenStore {
  private static REFRESH_KEY = 'hhps.refresh';
  private accessToken: string | null = null;
  private memoryRefresh: string | null = null;

  getAccess(): string | null {
    return this.accessToken;
  }
  setAccess(token: string | null): void {
    this.accessToken = token;
  }

  getRefresh(): string | null {
    try {
      if (typeof localStorage !== 'undefined' && typeof localStorage.getItem === 'function') {
        const stored = localStorage.getItem(TokenStore.REFRESH_KEY);
        if (stored !== null) return stored;
      }
    } catch {
      // Some test runtimes provide a broken localStorage; fall back to memory.
    }
    return this.memoryRefresh;
  }

  setRefresh(token: string | null): void {
    this.memoryRefresh = token;
    try {
      if (typeof localStorage !== 'undefined' && typeof localStorage.setItem === 'function') {
        if (token === null) localStorage.removeItem(TokenStore.REFRESH_KEY);
        else localStorage.setItem(TokenStore.REFRESH_KEY, token);
      }
    } catch {
      // Ignore broken localStorage; memoryRefresh is the source of truth here.
    }
  }

  clear(): void {
    this.accessToken = null;
    this.setRefresh(null);
  }
}

export const tokens = new TokenStore();

async function readError(r: Response): Promise<string> {
  try {
    const data = await r.clone().json();
    if (data && typeof data === 'object' && 'detail' in data) return String(data.detail);
  } catch {
    // ignore
  }
  return r.statusText || `HTTP ${r.status}`;
}

export async function login(email: string, password: string): Promise<LoginResponse> {
  const r = await fetch(`${API_URL}/api/v1/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  if (!r.ok) throw new ApiError(r.status, await readError(r));
  const data = (await r.json()) as LoginResponse;
  tokens.setAccess(data.access);
  tokens.setRefresh(data.refresh);
  return data;
}

export async function refresh(): Promise<string> {
  const refreshToken = tokens.getRefresh();
  if (!refreshToken) throw new ApiError(401, 'no refresh token');
  const r = await fetch(`${API_URL}/api/v1/auth/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh: refreshToken }),
  });
  if (!r.ok) {
    tokens.clear();
    throw new ApiError(r.status, 'refresh failed');
  }
  const data = (await r.json()) as { access: string };
  tokens.setAccess(data.access);
  return data.access;
}

export function logout(): void {
  tokens.clear();
}

export async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const send = async (token: string | null): Promise<Response> => {
    const headers = new Headers(init.headers);
    if (token) headers.set('Authorization', `Bearer ${token}`);
    return fetch(`${API_URL}${path}`, { ...init, headers });
  };

  let r = await send(tokens.getAccess());
  if (r.status === 401 && tokens.getRefresh()) {
    try {
      const fresh = await refresh();
      r = await send(fresh);
    } catch {
      // refresh failed; surface the original 401
    }
  }
  return r;
}

export async function wsToken(): Promise<WsTokenResponse> {
  const r = await apiFetch('/api/v1/auth/ws-token', { method: 'POST' });
  if (!r.ok) throw new ApiError(r.status, await readError(r));
  return (await r.json()) as WsTokenResponse;
}
