import { clearSession, origin } from '@/lib/session';

export async function POST(request: Request): Promise<Response> {
  if (request.headers.get('origin') !== origin()) return new Response('Forbidden', {status: 403});
  await clearSession();
  return new Response(null, {status: 204, headers: {'Cache-Control': 'no-store'}});
}
