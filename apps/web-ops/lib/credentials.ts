/**
 * Credential hierarchy — mirror of apps/api/scheduling/adapter.py:_CRED_RANK.
 *
 * RN > LVN > MA, all rank-comparable. phlebotomist is a standalone skill that
 * matches only itself.
 */

export const CREDENTIAL_RANK: Readonly<Record<string, number>> = {
  MA: 1,
  LVN: 2,
  RN: 3,
};

export function canServe(clinicianCredential: string, requiredSkill: string): boolean {
  if (clinicianCredential === 'phlebotomist' || requiredSkill === 'phlebotomist') {
    return clinicianCredential === requiredSkill;
  }
  const c = CREDENTIAL_RANK[clinicianCredential] ?? 0;
  const s = CREDENTIAL_RANK[requiredSkill] ?? 0;
  return c >= s;
}
