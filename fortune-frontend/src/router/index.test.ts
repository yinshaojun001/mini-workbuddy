// @vitest-environment jsdom
import { describe, expect, it } from 'vitest'
import { createMemoryHistory } from 'vue-router'
import { createPublicRouter } from './index'

describe('public router', () => {
  it('redirects the root and unknown paths to fortune', async () => {
    const router = createPublicRouter(createMemoryHistory())
    await router.push('/')
    await router.isReady()

    expect(router.currentRoute.value.path).toBe('/fortune')
    expect(router.currentRoute.value.redirectedFrom?.path).toBe('/')

    await router.push('/not-a-public-app')
    expect(router.currentRoute.value.path).toBe('/fortune')
  })

  it('exposes the fortune route without a placeholder dream route', () => {
    const router = createPublicRouter(createMemoryHistory())
    const routes = router.getRoutes()
    expect(routes.some((route) => route.path === '/fortune')).toBe(true)
    expect(routes.some((route) => route.path === '/dream')).toBe(false)
  })
})
