import { expect, test, type Page } from '@playwright/test'

const dreamContext = {
  kind: 'dream',
  summary: { emotions: ['焦虑', '怀念'], recurring: false },
  symbols: [{ id: 'house', label: '房屋' }, { id: 'water', label: '水' }],
  reference_index_version: '1.0.0',
}
const dreamSession = { id: 'dream-12345678', status: 'context_ready', expires_at: '2026-07-30T10:00:00Z', remaining_questions: 20 }
const locations = [{ code: '110000', parent_code: 'CN', name: '北京市', level: 'province' }, { code: '110100', parent_code: '110000', name: '北京市', level: 'city' }]

async function mockDreamApi(page: Page) {
  let reportReady = false
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
      quota: { remaining: 3, resets_at: '' },
    },
  }))
  await page.route('**/api/public/apps/dream/sessions', (route) => route.fulfill({ status: 201, json: { session: dreamSession, context: dreamContext, messages: [], quota: { daily_limit: 3, remaining: 2, resets_at: '' } } }))
  await page.route('**/api/public/apps/dream/sessions/*/report', async (route) => {
    reportReady = true
    await route.fulfill({ contentType: 'text/event-stream', body: `data: ${JSON.stringify({ type: 'run.started', data: {} })}\n\ndata: ${JSON.stringify({ type: 'message.delta', data: { content: '## 梦境速写\n旧屋和积水可以先作为过渡压力的线索。' } })}\n\ndata: ${JSON.stringify({ type: 'run.completed', data: {} })}\n\n` })
  })
  await page.route('**/api/public/apps/dream/sessions/*', (route) => route.fulfill({ json: { session: { ...dreamSession, status: reportReady ? 'report_ready' : 'context_ready' }, context: dreamContext, messages: reportReady ? [{ id: 'm1', role: 'assistant', content: '## 梦境速写\n旧屋和积水可以先作为过渡压力的线索。', created_at: '' }] : [] } }))
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
