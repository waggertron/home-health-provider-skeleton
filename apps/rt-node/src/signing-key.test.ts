import { createHash } from 'node:crypto';
import { describe, expect, it } from 'vitest';
import { deriveSigningKey } from './signing-key.js';

describe('deriveSigningKey', () => {
  it('returns the raw key when it is 32+ bytes', () => {
    const raw = 'a'.repeat(32);
    expect(deriveSigningKey(raw)).toBe(raw);
  });

  it('returns the raw key for a longer key', () => {
    const raw = 'a'.repeat(100);
    expect(deriveSigningKey(raw)).toBe(raw);
  });

  it('returns sha256-hex of the raw key when shorter than 32 bytes', () => {
    const raw = 'dev-secret-do-not-use-in-prod'; // 29 chars
    const expected = createHash('sha256').update(raw, 'utf8').digest('hex');
    expect(deriveSigningKey(raw)).toBe(expected);
    expect(expected).toHaveLength(64);
  });

  it('counts utf-8 bytes, not characters, for the boundary', () => {
    // "é" is 2 bytes in utf-8; 16 of them = 32 bytes → passes.
    const raw = 'é'.repeat(16);
    expect(deriveSigningKey(raw)).toBe(raw);
  });
});
