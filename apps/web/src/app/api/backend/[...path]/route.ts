import { clearSession, getSession, origin } from '@/lib/session';

async function proxy(request: Request, context: {params: Promise<{path: string[]}>}): Promise<Response> {
  const session = await getSession();
  const fail = (code: string, status: number) => Response.json({error: {code, message: code.replaceAll('_', ' ')}}, {status});
  if (!session) return fail('session_expired', 401);
  if (request.method === 'POST' && request.headers.get('origin') !== origin()) return fail('forbidden', 403);
  const {path} = await context.params;
  if (path[0] !== 'v1' || !path.every(segment => /^[a-zA-Z0-9_-]+$/.test(segment))) return fail('not_found', 404);
  const base = process.env.ATELIER_API_BASE_URL;
  if (!base) return fail('workspace_unavailable', 503);
  const endpoint = new URL(base);
  if (endpoint.protocol !== 'https:' && !['127.0.0.1', 'localhost'].includes(endpoint.hostname)) return fail('workspace_unavailable', 503);
  const headers: Record<string, string> = {Authorization: `Bearer ${session.accessToken}`};
  let body: string | undefined;
  if (request.method === 'POST') {
    headers['Content-Type'] = 'application/json';
    const key = request.headers.get('idempotency-key');
    if (!key || !/^[a-zA-Z0-9_.:-]{1,128}$/.test(key)) return fail('invalid_payload', 422);
    headers['Idempotency-Key'] = key;
    const reader = request.body?.getReader();
    if (!reader) return fail('invalid_payload', 422);
    const chunks: Uint8Array[] = [];
    let length = 0;
    while (true) {
      const {done, value} = await reader.read();
      if (done) break;
      length += value.length;
      if (length > 1_048_576) { await reader.cancel(); return fail('payload_too_large', 413); }
      chunks.push(value);
    }
    body = Buffer.concat(chunks).toString('utf8');
    try { JSON.parse(body); } catch { return fail('invalid_payload', 422); }
  }
  try {
    const incoming = new URL(request.url);
    const response = await fetch(`${endpoint.origin}/${path.join('/')}${incoming.search}`, {
      method: request.method, headers, body, cache: 'no-store', redirect: 'error', signal: AbortSignal.timeout(20_000),
    });
    if (response.status === 401) await clearSession();
    const isHandoffPdf = request.method === 'GET' && path.length === 6 &&
      path[1] === 'garments' && path[3] === 'handoff' && ['pdf', 'html'].includes(path[5]);
    const exportType = path[5] === 'html' ? 'text/html' : 'application/pdf';
    if (isHandoffPdf && response.ok && response.headers.get('content-type')?.split(';')[0].trim().toLowerCase() === exportType) {
      const reader = response.body?.getReader();
      if (!reader) return fail('workspace_unavailable', 502);
      const chunks: Uint8Array[] = [];
      let length = 0;
      while (true) {
        const {done, value} = await reader.read();
        if (done) break;
        length += value.length;
        if (length > 2_097_152) { await reader.cancel(); return fail('workspace_unavailable', 502); }
        chunks.push(value);
      }
      return new Response(Buffer.concat(chunks), {status: response.status, headers: {
        'Content-Type': exportType, 'Content-Disposition': `attachment; filename="atelier-handoff.${path[5]}"`,
        'Content-Security-Policy': "sandbox; default-src 'none'",
        'Cache-Control': 'private, no-store', 'X-Content-Type-Options': 'nosniff',
      }});
    }
    if (!response.headers.get('content-type')?.includes('application/json')) return fail('workspace_unavailable', 502);
    return Response.json(await response.json(), {status: response.status, headers: {'Cache-Control': 'no-store'}});
  } catch { return fail('workspace_unavailable', 503); }
}

export const GET = proxy;
export const POST = proxy;
