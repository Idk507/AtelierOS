import { randomBytes, createHash } from 'node:crypto';
import { cookies } from 'next/headers';
import { configured, flowCookie, origin, seal } from '@/lib/session';

export async function GET(): Promise<Response> {
  if (!configured()) return Response.json({error: 'Workspace sign-in is unavailable'}, {status: 503});
  const state = randomBytes(32).toString('base64url');
  const nonce = randomBytes(32).toString('base64url');
  const verifier = randomBytes(48).toString('base64url');
  const destination = new URL(process.env.ATELIER_OIDC_AUTHORIZATION_ENDPOINT!);
  if (destination.protocol !== 'https:' && !['localhost', '127.0.0.1'].includes(destination.hostname)) {
    return Response.json({error: 'Workspace sign-in is unavailable'}, {status: 503});
  }
  const params = {response_type: 'code', client_id: process.env.ATELIER_OIDC_CLIENT_ID!,
    redirect_uri: `${origin()}/auth/callback`, scope: process.env.ATELIER_OIDC_SCOPE || 'openid profile',
    state, nonce, code_challenge_method: 'S256',
    code_challenge: createHash('sha256').update(verifier).digest('base64url')};
  for (const [key, value] of Object.entries(params)) destination.searchParams.set(key, value);
  (await cookies()).set('atelier-flow', await seal({state, nonce, verifier}, 600), flowCookie);
  return Response.redirect(destination, 303);
}
