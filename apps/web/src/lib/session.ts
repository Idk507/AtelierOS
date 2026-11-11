import { cookies } from 'next/headers';
import { EncryptJWT, jwtDecrypt } from 'jose';

const name = 'atelier-session';
export interface Session { accessToken: string; subject: string; organizationId: string; exp: number }
const secure = process.env.NODE_ENV === 'production';

export function origin(): string {
  const value = process.env.ATELIER_WEB_ORIGIN;
  if (!value) throw new Error('Workspace origin is not configured');
  const url = new URL(value);
  if (url.pathname !== '/' || url.search || url.hash || url.username || url.password) {
    throw new Error('Invalid workspace origin');
  }
  if (url.protocol !== 'https:' && !['127.0.0.1', 'localhost'].includes(url.hostname)) {
    throw new Error('Workspace requires HTTPS');
  }
  return url.origin;
}

function key(): Uint8Array {
  const secret = process.env.ATELIER_SESSION_KEY;
  if (!secret) throw new Error('Session encryption is not configured');
  const bytes = Buffer.from(secret, 'base64');
  if (bytes.length !== 32) throw new Error('Session encryption requires 32 bytes');
  return bytes;
}

export async function seal(payload: Record<string, unknown>, seconds: number): Promise<string> {
  return new EncryptJWT(payload).setProtectedHeader({alg: 'dir', enc: 'A256GCM'})
    .setIssuer('atelier-session').setAudience('atelier-web').setIssuedAt()
    .setExpirationTime(`${seconds}s`).encrypt(key());
}

export async function unseal(value: string): Promise<Record<string, unknown>> {
  const {payload} = await jwtDecrypt(value, key(), {issuer: 'atelier-session', audience: 'atelier-web',
    keyManagementAlgorithms: ['dir'], contentEncryptionAlgorithms: ['A256GCM']});
  return payload;
}

export async function getSession(): Promise<Session | null> {
  const value = (await cookies()).get(name)?.value;
  if (!value) return null;
  try {
    const data = await unseal(value);
    if (typeof data.accessToken !== 'string' || typeof data.subject !== 'string' ||
        typeof data.organizationId !== 'string' || typeof data.exp !== 'number') return null;
    return data as unknown as Session;
  } catch { return null; }
}

export async function setSession(session: Session): Promise<void> {
  const age = Math.min(session.exp - Math.floor(Date.now() / 1000), 8 * 3600);
  if (age <= 0) throw new Error('Expired session');
  (await cookies()).set(name, await seal({...session}, age), {
    httpOnly: true, secure, sameSite: 'lax', path: '/', maxAge: age,
  });
}

export async function clearSession(): Promise<void> {
  (await cookies()).delete(name);
}

export const flowCookie = {httpOnly: true, secure, sameSite: 'lax' as const, path: '/', maxAge: 600};

export function configured(): boolean {
  return Boolean(process.env.ATELIER_OIDC_AUTHORIZATION_ENDPOINT && process.env.ATELIER_OIDC_TOKEN_ENDPOINT
    && process.env.ATELIER_OIDC_CLIENT_ID && process.env.ATELIER_SESSION_KEY
    && process.env.ATELIER_JWT_PUBLIC_KEY && process.env.ATELIER_WEB_ORIGIN
    && process.env.ATELIER_JWT_ISSUER && process.env.ATELIER_JWT_AUDIENCE && process.env.ATELIER_API_BASE_URL);
}
