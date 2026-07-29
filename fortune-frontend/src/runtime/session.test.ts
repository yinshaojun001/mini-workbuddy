// @vitest-environment jsdom
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { forgetSessionId, readSessionId, rememberSessionId, sessionKey } from './session'

describe('public runtime sessions', () => {
  beforeEach(() => {
    const values = new Map<string, string>()
    vi.stubGlobal('localStorage', {
      getItem: (key: string) => values.get(key) ?? null,
      setItem: (key: string, value: string) => values.set(key, value),
      removeItem: (key: string) => values.delete(key),
    })
  })

  it('uses independent localStorage keys per public app', () => {
    expect(sessionKey('fortune')).toBe('fortune_session_id')
    expect(sessionKey('dream')).toBe('dream_session_id')

    rememberSessionId('fortune', 'fortune-session')
    rememberSessionId('dream', 'dream-session')
    forgetSessionId('fortune')

    expect(readSessionId('fortune')).toBeNull()
    expect(readSessionId('dream')).toBe('dream-session')
  })
})
