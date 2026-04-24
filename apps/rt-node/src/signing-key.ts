import { createHash } from 'node:crypto';

/**
 * Mirror Django's SIMPLE_JWT signing-key derivation in hhps/settings.py:
 *     _SIGNING_KEY = SECRET_KEY if len(SECRET_KEY.encode()) >= 32
 *                    else sha256(SECRET_KEY.encode()).hexdigest()
 *
 * rt-node receives DJANGO_SECRET_KEY (not the derived key) so the two
 * services stay in sync regardless of how short the raw secret is.
 */
export function deriveSigningKey(raw: string): string {
  const bytes = Buffer.byteLength(raw, 'utf8');
  if (bytes >= 32) return raw;
  return createHash('sha256').update(raw, 'utf8').digest('hex');
}
