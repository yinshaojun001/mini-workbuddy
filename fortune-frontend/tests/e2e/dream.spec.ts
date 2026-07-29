import { expect, test, type Page } from '@playwright/test'

const dreamContext = {
  kind: 'dream',
  summary: { emotions: ['焦虑', '怀念'], recurring: false },
  symbols: [{ id: 'house', label: '房屋' }, { id: 'water', label: '水' }],
  reference_index_version: '1.0.0',
}
const dreamSession = { id: 'dream-12345678', status: 'context_ready', expires_at: '2026-07-30T10:00:00Z', remaining_questions: 20 }
const locations = [{ code: '110000', parent_code: 'CN', name: '北京市', level: 'province' }, { code: '110100', parent_code: '110000', name: '北京市', level: 'city' }]

interface DreamMockOptions {
  remaining?: number
  failFirstReport?: boolean
  restoreExpired?: boolean
  symbols?: Array<{ id: string; label: string }>
}

async function mockDreamApi(page: Page, options: DreamMockOptions = {}) {
  let reportReady = false
  let questionReady = false
  let reportAttempts = 0
  const state = { deleted: false }
  const context = { ...dreamContext, symbols: options.symbols ?? dreamContext.symbols }
  await page.route('**/api/public/apps/dream', (route) => route.fulfill({
    json: {
      name: '知梦',
      slug: 'dream',
      daily_limit: 3,
      ttl_hours: 24,
      max_questions: 20,
      form: {
        dream_text: { min_length: 20, max_length: 4000 },
        emotions: { options: ['害怕', '焦虑', '平静', '惊奇', '怀念', '悲伤', '愉悦', '困惑'], max_items: 3 },
        recent_context: { max_length: 500 },
        recurring: { type: 'boolean', default: false },
      },
      quota: { remaining: options.remaining ?? 3, resets_at: '2026-07-30T00:00:00+08:00' },
    },
  }))
  await page.route('**/api/public/apps/dream/sessions', (route) => route.fulfill({ status: 201, json: { session: dreamSession, context, messages: [], quota: { daily_limit: 3, remaining: 2, resets_at: '' } } }))
  await page.route('**/api/public/apps/dream/sessions/*/report', async (route) => {
    reportAttempts += 1
    if (options.failFirstReport && reportAttempts === 1) {
      await route.fulfill({ contentType: 'text/event-stream', body: `data: ${JSON.stringify({ type: 'run.failed', data: { code: 'MODEL_TIMEOUT', message: '解读服务暂时超时' } })}\n\n` })
      return
    }
    reportReady = true
    await route.fulfill({ contentType: 'text/event-stream', body: `data: ${JSON.stringify({ type: 'run.started', data: {} })}\n\ndata: ${JSON.stringify({ type: 'message.delta', data: { content: '## 梦境速写\n旧屋和积水可以先作为过渡压力的线索。' } })}\n\ndata: ${JSON.stringify({ type: 'run.completed', data: {} })}\n\n` })
  })
  await page.route('**/api/public/apps/dream/sessions/*/messages', async (route) => {
    questionReady = true
    await route.fulfill({ contentType: 'text/event-stream', body: `data: ${JSON.stringify({ type: 'message.delta', data: { content: '也可以留意近期对安全感的需要。' } })}\n\ndata: ${JSON.stringify({ type: 'run.completed', data: {} })}\n\n` })
  })
  await page.route('**/api/public/apps/dream/sessions/*', (route) => {
    if (route.request().method() === 'DELETE') {
      state.deleted = true
      return route.fulfill({ status: 204, body: '' })
    }
    if (options.restoreExpired) return route.fulfill({ status: 404, json: { error: { code: 'PUBLIC_SESSION_NOT_FOUND', message: '会话不存在或已过期' } } })
    const messages = reportReady ? [{ id: 'm1', role: 'assistant', content: '## 梦境速写\n旧屋和积水可以先作为过渡压力的线索。', created_at: '' }] : []
    if (questionReady) messages.push(
      { id: 'm2', role: 'user', content: '这个旧屋还可能代表什么？', created_at: '' },
      { id: 'm3', role: 'assistant', content: '也可以留意近期对安全感的需要。', created_at: '' },
    )
    return route.fulfill({ json: { session: { ...dreamSession, status: reportReady ? 'report_ready' : 'context_ready' }, context, messages } })
  })
  return state
}

async function mockFortuneMetadata(page: Page) {
  await page.route('**/api/public/apps/fortune', (route) => route.fulfill({
    json: { name: '知命', slug: 'fortune', daily_limit: 3, ttl_hours: 24, max_questions: 20, locations, quota: { remaining: 3, resets_at: '' } },
  }))
}

test('completes the dream form and renders a streamed interpretation', async ({ page }) => {
  await mockDreamApi(page)

  await page.goto('/dream')
  await page.getByLabel('梦境正文').fill('我梦见自己回到旧屋，地面不断积水，怎么也找不到出口。')
  await page.getByRole('button', { name: '焦虑' }).click()
  await page.getByRole('button', { name: '怀念' }).click()
  await page.getByRole('button', { name: '开始解梦' }).click()

  await expect(page.getByText('梦境速写').first()).toBeVisible()
  await expect(page.getByText('房屋')).toBeVisible()
  await expect(page.getByText('旧屋和积水可以先作为过渡压力的线索。')).toBeVisible()
  await expect(page.getByText('传统梦象参考整理自公版《周公解梦》，只作文化参照；心理与现实映照不是诊断或预言。')).toBeVisible()
  await page.screenshot({ path: 'test-results/dream-report-desktop.png', fullPage: true })
})

for (const width of [320, 390, 768, 1440]) {
  test(`has no page overflow at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: width < 600 ? 844 : 900 })
    await mockDreamApi(page)
    await page.goto('/dream')

    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
    expect(overflow).toBeLessThanOrEqual(0)
    if (width === 390) await page.screenshot({ path: 'test-results/dream-form-mobile.png', fullPage: true })
  })
}

test('keeps the dream local session while switching to fortune', async ({ page }) => {
  await mockDreamApi(page)
  await mockFortuneMetadata(page)

  await page.goto('/dream')
  await page.evaluate(() => {
    localStorage.setItem('dream_session_id', 'dream-session')
  })
  await page.getByRole('link', { name: '知命' }).first().click()

  await expect(page).toHaveURL(/\/fortune$/)
  await expect(page.evaluate(() => localStorage.getItem('dream_session_id'))).resolves.toBe('dream-session')
  await expect(page.evaluate(() => localStorage.getItem('fortune_session_id'))).resolves.toBeNull()
})

test('shows quota reset time when today is exhausted', async ({ page }) => {
  await mockDreamApi(page, { remaining: 0 })
  await page.goto('/dream')

  await expect(page.getByRole('button', { name: '今日额度已用完' })).toBeDisabled()
  await expect(page.getByText(/后恢复/)).toBeVisible()
})

test('keeps context and retries after a model failure', async ({ page }) => {
  await mockDreamApi(page, { failFirstReport: true })
  await page.goto('/dream')
  await page.getByLabel('梦境正文').fill('我梦见自己回到旧屋，地面不断积水，怎么也找不到出口。')
  await page.getByRole('button', { name: '开始解梦' }).click()

  await expect(page.getByText('解读服务暂时超时')).toBeVisible()
  await expect(page.getByText('房屋')).toBeVisible()
  await page.getByRole('button', { name: '生成解读' }).click()
  await expect(page.getByText('旧屋和积水可以先作为过渡压力的线索。')).toBeVisible()
})

test('expired dream restore clears only the dream session key', async ({ page }) => {
  await mockDreamApi(page, { restoreExpired: true })
  await page.addInitScript(() => {
    localStorage.setItem('dream_session_id', 'expired-dream')
    localStorage.setItem('fortune_session_id', 'active-fortune')
  })
  await page.goto('/dream')

  await expect(page.getByRole('button', { name: '开始解梦' })).toBeVisible()
  await expect(page.evaluate(() => localStorage.getItem('dream_session_id'))).resolves.toBeNull()
  await expect(page.evaluate(() => localStorage.getItem('fortune_session_id'))).resolves.toBe('active-fortune')
})

test('completes a no-match report and supports question then deletion', async ({ page }) => {
  const state = await mockDreamApi(page, { symbols: [] })
  page.on('dialog', (dialog) => dialog.accept())
  await page.goto('/dream')
  await page.getByLabel('梦境正文').fill('我梦见电梯没有按钮，一直在陌生星球横向移动。')
  await page.getByRole('button', { name: '开始解梦' }).click()

  await expect(page.getByText('未命中')).toBeVisible()
  await page.getByPlaceholder('基于这场梦继续提问').fill('这个旧屋还可能代表什么？')
  await page.getByTitle('发送追问').click()
  await expect(page.getByText('也可以留意近期对安全感的需要。')).toBeVisible()
  await page.getByRole('button', { name: '清除梦境' }).click()
  await expect(page.getByRole('button', { name: '开始解梦' })).toBeVisible()
  expect(state.deleted).toBe(true)
})
