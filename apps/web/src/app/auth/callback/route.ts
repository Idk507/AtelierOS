import { cookies } from 'next/headers';
import { importSPKI, jwtVerify } from 'jose';
import { configured, origin, setSession, unseal } from '@/lib/session';

export async function GET(request: Request): Promise<Response> {
  if (!configured()) return Response.json({error: 'Workspace sign-in is unavailable'}, {status: 503});
  const jar = await cookies();
  const flow = jar.get('atelier-flow')?.value;
  jar.delete('atelier-flow');
  try {
    const incoming = new URL(request.url);
    if (!flow || !incoming.searchParams.get('code')) throw new Error('Missing login');
    const {state, nonce, verifier} = await unseal(flow);
    if (typeof verifier !== 'string' || incoming.searchParams.get('state') !== state) {
      throw new Error('Invalid state');
    }
    const endpoint = new URL(process.env.ATELIER_OIDC_TOKEN_ENDPOINT!);
    if (endpoint.protocol !== 'https:' && !['localhost', '127.0.0.1'].includes(endpoint.hostname)) {
      throw new Error('Invalid token endpoint');
    }
    const form = new URLSearchParams({grant_type: 'authorization_code', code: incoming.searchParams.get('code')!,
      client_id: process.env.ATELIER_OIDC_CLIENT_ID!, redirect_uri: `${origin()}/auth/callback`,
      code_verifier: verifier});
    if (process.env.ATELIER_OIDC_CLIENT_SECRET) form.set('client_secret', process.env.ATELIER_OIDC_CLIENT_SECRET);
    const response = await fetch(endpoint, {method: 'POST', body: form, cache: 'no-store',
      signal: AbortSignal.timeout(10_000), redirect: 'error'});
    if (!response.ok) throw new Error('Token exchange failed');
    const data = await response.json();
    if (typeof data.id_token !== 'string' || typeof data.access_token !== 'string') throw new Error('Missing token');
    const key = await importSPKI(process.env.ATELIER_JWT_PUBLIC_KEY!, 'RS256');
    const {payload: id} = await jwtVerify(data.id_token, key, {algorithms: ['RS256'],
      issuer: process.env.ATELIER_JWT_ISSUER, audience: process.env.ATELIER_OIDC_CLIENT_ID,
      requiredClaims: ['exp', 'iat', 'sub', 'nonce']});
    if (id.nonce !== nonce) throw new Error('Invalid nonce');
    const {payload: access} = await jwtVerify(data.access_token, key, {algorithms: ['RS256'],
      issuer: process.env.ATELIER_JWT_ISSUER, audience: process.env.ATELIER_JWT_AUDIENCE,
      requiredClaims: ['exp', 'iat', 'nbf', 'sub', 'organization_id', 'principal_type']});
    if (access.sub !== id.sub || access.principal_type !== 'human' ||
        typeof access.organization_id !== 'string' || !access.sub || !access.exp) throw new Error('Invalid identity');
    await setSession({accessToken: data.access_token, subject: access.sub,
      organizationId: access.organization_id, exp: access.exp});
    return Response.redirect(`${origin()}/`, 303);
  } catch {
    return Response.redirect(`${origin()}/?sign_in=failed`, 303);
  }
}
