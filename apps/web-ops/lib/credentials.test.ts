import { describe, expect, it } from 'vitest';
import { canServe } from './credentials';

describe('canServe', () => {
  it('higher-rank credential serves a lower-rank skill', () => {
    expect(canServe('RN', 'MA')).toBe(true);
    expect(canServe('RN', 'LVN')).toBe(true);
    expect(canServe('LVN', 'MA')).toBe(true);
    expect(canServe('RN', 'RN')).toBe(true);
  });

  it('lower-rank credential cannot serve a higher-rank skill', () => {
    expect(canServe('MA', 'LVN')).toBe(false);
    expect(canServe('MA', 'RN')).toBe(false);
    expect(canServe('LVN', 'RN')).toBe(false);
  });

  it('phlebotomist requires an exact match', () => {
    expect(canServe('phlebotomist', 'phlebotomist')).toBe(true);
  });

  it('phlebotomist cannot serve hierarchical skills (and vice versa)', () => {
    expect(canServe('phlebotomist', 'MA')).toBe(false);
    expect(canServe('phlebotomist', 'RN')).toBe(false);
    expect(canServe('RN', 'phlebotomist')).toBe(false);
    expect(canServe('LVN', 'phlebotomist')).toBe(false);
  });
});
