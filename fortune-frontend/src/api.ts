import type { BirthPayload, PublicMetadata, SessionPayload, SseEvent } from './types'
import { consumeSse } from './sse'

async function errorMessage(response: Response) {
  try { return (await response.json()).error?.message || `请求失败（${response.status}）` } catch { return `请求失败（${response.status}）` }
}

export async function getMetadata(): Promise<PublicMetadata> {
  const response = await fetch('/api/public/apps/fortune', { credentials: 'include' })
  if (!response.ok) throw new Error(await errorMessage(response))
  return response.json()
}

export async function createSession(payload: BirthPayload): Promise<SessionPayload> {
  const response = await fetch('/api/public/apps/fortune/sessions', { method: 'POST', credentials: 'include', headers: { 'content-type': 'application/json' }, body: JSON.stringify(payload) })
  if (!response.ok) throw new Error(await errorMessage(response))
  return response.json()
}

export async function getSession(id: string): Promise<SessionPayload> {
  const response = await fetch(`/api/public/apps/fortune/sessions/${id}`, { credentials: 'include' })
  if (!response.ok) throw new Error(await errorMessage(response))
  return response.json()
}

export async function deleteSession(id: string): Promise<void> {
  const response = await fetch(`/api/public/apps/fortune/sessions/${id}`, { method: 'DELETE', credentials: 'include' })
  if (!response.ok) throw new Error(await errorMessage(response))
}

export async function streamRun(id: string, mode: 'report' | 'messages', content: string | undefined, onEvent: (event: SseEvent) => void) {
  const response = await fetch(`/api/public/apps/fortune/sessions/${id}/${mode}`, {
    method: 'POST', credentials: 'include', headers: content ? { 'content-type': 'application/json' } : undefined,
    body: content ? JSON.stringify({ content }) : undefined,
  })
  if (!response.ok) throw new Error(await errorMessage(response))
  if (!response.body) throw new Error('浏览器不支持流式响应')
  await consumeSse(response.body, onEvent)
}
