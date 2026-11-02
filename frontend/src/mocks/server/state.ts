import 'server-only';
import { createHmac, randomBytes, randomUUID, timingSafeEqual } from 'node:crypto';
import type { User, CaseStatus, Kind } from '@/lib/api/types';
interface Family {
  user: User;
  expires: number;
  revoked: boolean;
}
interface Access {
  family: Family;
  expires: number;
}
interface Refresh {
  family: Family;
  consumed: boolean;
}
interface StoredCase extends CaseStatus {
  caseNo: string;
  kind: Kind;
  ownerId: string;
  sessionId: string;
}
interface DemoState {
  intakes: Map<
    string,
    { kind: Kind; stage: 'collecting' | 'readback' | 'confirmed'; expires: number }
  >;
  secret: Buffer;
  users: Map<string, User>;
  access: Map<string, Access>;
  refresh: Map<string, Refresh>;
  challenges: Map<string, number>;
  limits: Map<string, { count: number; expires: number }>;
  cases: Map<string, StoredCase>;
  sequence: number;
}
const globalState = globalThis as typeof globalThis & { khojDemo?: DemoState };
export const state = (globalState.khojDemo ??= {
  intakes: new Map(),
  secret: randomBytes(32),
  users: new Map(),
  access: new Map(),
  refresh: new Map(),
  challenges: new Map(),
  limits: new Map(),
  cases: new Map(),
  sequence: 0,
});
state.intakes ??= new Map();
export const digest = (value: string) =>
  createHmac('sha256', state.secret).update(value).digest('hex');
export function limit(key: string, maximum: number) {
  const now = Date.now();
  let entry = state.limits.get(key);
  if (!entry || entry.expires <= now) {
    entry = { count: 0, expires: now + 3600000 };
    state.limits.set(key, entry);
  }
  entry.count++;
  return entry.count > maximum ? Math.ceil((entry.expires - now) / 1000) : 0;
}
export function getUser(phone: string): User {
  const hash = digest(phone);
  let user = state.users.get(hash);
  if (!user) {
    const roles: Record<string, User['role']> = {
      '9000000001': 'citizen',
      '9000000002': 'volunteer',
      '9000000003': 'officer',
      '9000000004': 'admin',
    };
    const role = roles[phone] || 'citizen';
    user = { id: randomUUID(), role, lang: 'hi', phoneSuffix: phone.slice(-2) };
    state.users.set(hash, user);
  }
  return user;
}
export function issue(user: User, family?: Family) {
  const current = family || { user, expires: Date.now() + 7 * 86400000, revoked: false };
  const access = randomBytes(32).toString('base64url'),
    refresh = randomBytes(32).toString('base64url');
  state.access.set(digest(access), { family: current, expires: Date.now() + 900000 });
  state.refresh.set(digest(refresh), { family: current, consumed: false });
  return { access, refresh };
}
export function validAccess(token: string | undefined) {
  const entry = token ? state.access.get(digest(token)) : undefined;
  return entry &&
    !entry.family.revoked &&
    entry.expires > Date.now() &&
    entry.family.expires > Date.now()
    ? entry.family.user
    : null;
}
export function verifyCode(code: string) {
  const actual = Buffer.from(code),
    expected = Buffer.from('123456');
  return actual.length === expected.length && timingSafeEqual(actual, expected);
}
export function saveCase(owner: User, kind: Kind, sessionId: string) {
  const existing = [...state.cases.values()].find(
    (c) => c.ownerId === owner.id && c.sessionId === sessionId,
  );
  if (existing) return existing.caseNo;
  const at = new Date().toISOString();
  const year = new Intl.DateTimeFormat('en', { year: 'numeric', timeZone: 'Asia/Kolkata' }).format(
    new Date(),
  );
  const caseNo = `KHJ-${year}-${String(++state.sequence).padStart(5, '0')}`;
  state.cases.set(caseNo, {
    caseNo,
    kind,
    ownerId: owner.id,
    sessionId,
    status: 'Active demo report',
    lastCheckedAt: at,
    recordsChecked: 0,
    pendingReview: 0,
    timeline: [{ at, text: 'Demo report saved. No police records have been checked.' }],
  });
  return caseNo;
}
