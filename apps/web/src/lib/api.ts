const pending = new Map<string, string>();

export class ApiError extends Error {
  constructor(public code: string, public status: number) { super(code.replaceAll('_', ' ')); }
}

export async function api<T>(path: string, body?: unknown): Promise<T> {
  const digest = body === undefined ? '' : `${path}:${JSON.stringify(body)}`;
  const key = pending.get(digest) || crypto.randomUUID();
  if (body !== undefined) pending.set(digest, key);
  let response: Response;
  try {
    response = await fetch(`/api/backend/v1${path}`, {method: body === undefined ? 'GET' : 'POST',
      headers: body === undefined ? undefined : {'Content-Type': 'application/json', 'Idempotency-Key': key},
      body: body === undefined ? undefined : JSON.stringify(body), cache: 'no-store'});
  } catch { throw new ApiError('connection_interrupted_retry_safely', 0); }
  const data = await response.json();
  if (response.ok || (response.status >= 400 && response.status < 500)) pending.delete(digest);
  if (!response.ok) throw new ApiError(data.error?.code || 'workspace_unavailable', response.status);
  return data as T;
}
