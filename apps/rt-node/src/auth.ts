import jwt from 'jsonwebtoken';

export interface AuthClaims {
  tenantId: number;
  role: string;
}

/**
 * Verify a WS auth token minted by Django's /auth/ws-token endpoint.
 * Returns the extracted claims on success, or null for any failure
 * (invalid signature, expired, wrong scope, malformed payload).
 */
export function verifyToken(token: string, signingKey: string): AuthClaims | null {
  if (!token || !signingKey) return null;
  let payload: jwt.JwtPayload;
  try {
    const decoded = jwt.verify(token, signingKey);
    if (typeof decoded === 'string') return null;
    payload = decoded;
  } catch {
    return null;
  }

  if (payload.scope !== 'ws') return null;

  const tenantId = Number(payload.tenant_id);
  const role = payload.role;
  if (!Number.isFinite(tenantId) || tenantId <= 0) return null;
  if (typeof role !== 'string' || role.length === 0) return null;

  return { tenantId, role };
}
