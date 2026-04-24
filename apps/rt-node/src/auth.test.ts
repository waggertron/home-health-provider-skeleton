import jwt from 'jsonwebtoken';
import { describe, expect, it } from 'vitest';
import { verifyToken } from './auth.js';

const KEY = 'test-signing-key-at-least-32-bytes-xxxxxxxxxxxxxxxxxxxx';

function mint(overrides: Record<string, unknown> = {}, expiresIn = 60): string {
  return jwt.sign(
    { tenant_id: 1, role: 'scheduler', scope: 'ws', ...overrides },
    KEY,
    { algorithm: 'HS256', expiresIn },
  );
}

describe('verifyToken', () => {
  it('returns claims for a valid ws-scoped token', () => {
    const token = mint();
    expect(verifyToken(token, KEY)).toEqual({ tenantId: 1, role: 'scheduler' });
  });

  it('rejects a token signed with a different key', () => {
    const token = mint();
    expect(verifyToken(token, 'wrong-key-must-also-be-long-enough-xxxxxxxxx')).toBeNull();
  });

  it('rejects a token without scope=ws', () => {
    const token = mint({ scope: 'access' });
    expect(verifyToken(token, KEY)).toBeNull();
  });

  it('rejects an expired token', () => {
    const token = mint({}, -10);
    expect(verifyToken(token, KEY)).toBeNull();
  });

  it('rejects a malformed token string', () => {
    expect(verifyToken('not-a-jwt', KEY)).toBeNull();
  });

  it('rejects an empty token or empty key', () => {
    expect(verifyToken('', KEY)).toBeNull();
    expect(verifyToken(mint(), '')).toBeNull();
  });

  it('rejects a token missing tenant_id or role', () => {
    const noTenant = jwt.sign({ role: 'scheduler', scope: 'ws' }, KEY, { expiresIn: 60 });
    const noRole = jwt.sign({ tenant_id: 1, scope: 'ws' }, KEY, { expiresIn: 60 });
    expect(verifyToken(noTenant, KEY)).toBeNull();
    expect(verifyToken(noRole, KEY)).toBeNull();
  });
});
