export interface ApiErrorBody { error?: { code: string; message: string; details?: Record<string, unknown> } }

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers)
  if (!(init?.body instanceof FormData)) headers.set('Content-Type', 'application/json')
  const response = await fetch(path, { ...init, headers })
  if (!response.ok) {
    let body: ApiErrorBody = {}
    try { body = await response.json() } catch { /* empty response */ }
    throw new Error(body.error?.message || `请求失败（${response.status}）`)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export function jsonBody(value: unknown): RequestInit {
  return { body: JSON.stringify(value) }
}

