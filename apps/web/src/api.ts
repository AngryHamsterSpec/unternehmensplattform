export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public requestId?: string,
    public fields?: unknown,
  ) {
    super(message);
  }
}

export async function request<T>(
  path: string,
  options: {
    method?: string;
    body?: unknown;
    rawBody?: Blob;
    csrf?: string;
    idempotencyKey?: string;
    signal?: AbortSignal;
  } = {},
): Promise<T> {
  const headers = new Headers({ Accept: 'application/json' });
  if (options.body !== undefined) headers.set('Content-Type', 'application/json');
  if (options.rawBody) headers.set('Content-Type', 'application/octet-stream');
  if (options.csrf) headers.set('X-CSRF-Token', options.csrf);
  if (options.idempotencyKey) headers.set('Idempotency-Key', options.idempotencyKey);
  let response: Response;
  try {
    response = await fetch(`/api/v1${path}`, {
      method: options.method ?? 'GET',
      headers,
      credentials: 'same-origin',
      body:
        options.rawBody ?? (options.body === undefined ? undefined : JSON.stringify(options.body)),
      signal: options.signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error;
    throw new ApiError(
      'Der Server ist nicht erreichbar. Bitte die Verbindung prüfen und erneut versuchen.',
      0,
    );
  }
  const data = (await response.json().catch(() => null)) as Record<string, unknown> | null;
  if (!response.ok) {
    const detail =
      typeof data?.detail === 'string'
        ? data.detail
        : typeof data?.title === 'string'
          ? data.title
          : 'Die Anfrage konnte nicht ausgeführt werden.';
    throw new ApiError(
      response.status === 401 ? 'Die Sitzung ist abgelaufen. Bitte erneut anmelden.' : detail,
      response.status,
      typeof data?.request_id === 'string' ? data.request_id : undefined,
      data?.field_errors ?? (Array.isArray(data?.detail) ? data.detail : undefined),
    );
  }
  if (data === null && response.status !== 204) {
    throw new ApiError('Die Serverantwort ist unvollständig. Bitte erneut versuchen.', 502);
  }
  return data as T;
}

export function isAbort(error: unknown) {
  return error instanceof DOMException && error.name === 'AbortError';
}
export function errorText(error: unknown) {
  return error instanceof Error ? error.message : 'Ein unerwarteter Fehler ist aufgetreten.';
}
