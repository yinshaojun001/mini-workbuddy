import type {
  PublicRunDetail,
  PublicRunsListQuery,
  PublicRunsListResponse,
  PublicRunStats,
} from '@/types'

export interface ApiErrorBody {
  error?: {
    code?: string
    message?: string
    details?: unknown
  }
}

export class ApiRequestError extends Error {
  readonly status: number
  readonly code: string
  readonly details: Record<string, unknown>

  constructor(status: number, code: string, message: string, details: Record<string, unknown> = {}) {
    super(message)
    this.name = 'ApiRequestError'
    this.status = status
    this.code = code
    this.details = details
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers)
  if (!(init?.body instanceof FormData)) headers.set('Content-Type', 'application/json')
  const response = await fetch(path, { ...init, headers })
  if (!response.ok) {
    let body: ApiErrorBody = {}
    try { body = await response.json() } catch { /* empty response */ }
    const error = isRecord(body.error) ? body.error : undefined
    const code = typeof error?.code === 'string' ? error.code : 'HTTP_ERROR'
    const message = typeof error?.message === 'string'
      ? error.message
      : `请求失败（${response.status}）`
    const details = isRecord(error?.details) ? error.details : {}
    throw new ApiRequestError(response.status, code, message, details)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export function jsonBody(value: unknown): RequestInit {
  return { body: JSON.stringify(value) }
}

export function listPublicRuns(params: PublicRunsListQuery = {}): Promise<PublicRunsListResponse> {
  const query = new URLSearchParams()
  if (params.app_id) query.set('app_id', params.app_id)
  if (params.status) query.set('status', params.status)
  if (params.query) query.set('query', params.query)
  if (params.limit !== undefined) query.set('limit', String(params.limit))
  if (params.cursor) query.set('cursor', params.cursor)
  const suffix = query.size ? `?${query.toString()}` : ''
  return api<PublicRunsListResponse>(`/api/public-runs${suffix}`)
}

export function getPublicRun(
  sessionId: string,
  includeSensitive = false,
): Promise<PublicRunDetail> {
  const query = new URLSearchParams()
  if (includeSensitive) query.set('include_sensitive', 'true')
  const suffix = query.size ? `?${query.toString()}` : ''
  return api<PublicRunDetail>(`/api/public-runs/${encodeURIComponent(sessionId)}${suffix}`)
}

export function getPublicRunStats(): Promise<PublicRunStats> {
  return api<PublicRunStats>('/api/public-runs/stats')
}

export function deletePublicRun(sessionId: string): Promise<void> {
  return api<void>(`/api/public-runs/${encodeURIComponent(sessionId)}`, { method: 'DELETE' })
}
