import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  ApiRequestError,
  api,
  deletePublicRun,
  listPublicRuns,
} from './client'

afterEach(() => vi.unstubAllGlobals())

describe('api', () => {
  it('returns parsed JSON responses', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({ status: 'ok' }), {
      status: 200,
      headers: { 'content-type': 'application/json' },
    })))

    await expect(api<{ status: string }>('/api/health')).resolves.toEqual({ status: 'ok' })
  })

  it('returns undefined for 204 responses without parsing a body', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(null, { status: 204 })))

    await expect(deletePublicRun('c8cc159f-24ec-4388-9154-f17550fc588f')).resolves.toBeUndefined()
  })

  it('preserves structured error status, code, message, and details', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({
      error: {
        code: 'SESSION_RUNNING',
        message: '当前运行结束后才能删除',
        details: { session_id: 'c8cc159f-24ec-4388-9154-f17550fc588f' },
      },
    }), {
      status: 409,
      headers: { 'content-type': 'application/json' },
    })))

    const error = await api('/api/public-runs/c8cc159f-24ec-4388-9154-f17550fc588f')
      .catch((reason: unknown) => reason)

    expect(error).toBeInstanceOf(ApiRequestError)
    expect(error).toMatchObject({
      name: 'ApiRequestError',
      status: 409,
      code: 'SESSION_RUNNING',
      message: '当前运行结束后才能删除',
      details: { session_id: 'c8cc159f-24ec-4388-9154-f17550fc588f' },
    })
    expect((error as Error).message).toBe('当前运行结束后才能删除')
  })

  it('uses a stable generic ApiRequestError for non-JSON failures', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response('<html>bad gateway</html>', {
      status: 502,
      headers: { 'content-type': 'text/html' },
    })))

    const error = await api('/api/public-runs').catch((reason: unknown) => reason)

    expect(error).toBeInstanceOf(ApiRequestError)
    expect(error).toMatchObject({
      status: 502,
      code: 'HTTP_ERROR',
      message: '请求失败（502）',
      details: {},
    })
  })
})

describe('public run requests', () => {
  it('encodes list filters with URLSearchParams', async () => {
    const fetchMock = vi.fn(async (_input: RequestInfo | URL) => new Response(JSON.stringify({
      items: [],
      next_cursor: null,
      refreshed_at: '2026-07-26T00:00:00+00:00',
    }), {
      status: 200,
      headers: { 'content-type': 'application/json' },
    }))
    vi.stubGlobal('fetch', fetchMock)

    await listPublicRuns({
      app_id: 'fortune app',
      status: 'failed',
      query: '失败/会话',
      limit: 25,
      cursor: 'anchor+value=',
    })

    const requested = new URL(String(fetchMock.mock.calls[0]?.[0]), 'http://localhost')
    expect(requested.pathname).toBe('/api/public-runs')
    expect(Object.fromEntries(requested.searchParams)).toEqual({
      app_id: 'fortune app',
      status: 'failed',
      query: '失败/会话',
      limit: '25',
      cursor: 'anchor+value=',
    })
  })
})
