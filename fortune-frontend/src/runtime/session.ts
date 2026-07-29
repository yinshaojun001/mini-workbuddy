import type { PublicAppSlug } from '@/types'

const SESSION_KEYS: Record<PublicAppSlug, string> = {
  fortune: 'fortune_session_id',
  dream: 'dream_session_id',
}

export function sessionKey(slug: PublicAppSlug): string {
  return SESSION_KEYS[slug]
}

export function readSessionId(slug: PublicAppSlug): string | null {
  return localStorage.getItem(sessionKey(slug))
}

export function rememberSessionId(slug: PublicAppSlug, id: string): void {
  localStorage.setItem(sessionKey(slug), id)
}

export function forgetSessionId(slug: PublicAppSlug): void {
  localStorage.removeItem(sessionKey(slug))
}
