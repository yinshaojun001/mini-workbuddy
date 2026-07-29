import { expect, test, type Page } from '@playwright/test'

const locations = [{ code: '110000', parent_code: 'CN', name: '北京市', level: 'province' }, { code: '110100', parent_code: '110000', name: '北京市', level: 'city' }]
const chart = { input: { name: null, gender: 'female', birth_date: '1998-12-13', birth_time: '12:00', birth_time_unknown: false, province_code: '110000', city_code: '110100', true_solar_time: false, focus_topics: ['career'] }, calculation_policy: { day_boundary_mode: 'ZI_HOUR_23' }, pillars: { year: { stem: '戊', branch: '寅', ganZhi: '戊寅', stemTenGod: '偏财', hiddenStems: [] }, month: { stem: '甲', branch: '子', ganZhi: '甲子', stemTenGod: '比肩', hiddenStems: [] }, day: { stem: '甲', branch: '午', ganZhi: '甲午', stemTenGod: '比肩', hiddenStems: [] }, hour: { stem: '庚', branch: '午', ganZhi: '庚午', stemTenGod: '七杀', hiddenStems: [] } }, day_master: { char: '甲', element: 'wood', polarity: 'yang' }, five_elements: { wood: 2, fire: 2, earth: 1, metal: 1, water: 2 }, ten_gods: {}, hidden_stems: {}, da_yun: { isForward: true, startAge: 2, cycles: [{ ganZhi: '乙丑', startAge: 2, endAge: 11, stemTenGod: '劫财' }, { ganZhi: '丙寅', startAge: 12, endAge: 21, stemTenGod: '食神' }] }, interactions: [], solar_time: null, attribution: { name: 'OpenFate.ai', url: 'https://openfate.ai' } }
const session = { id: '12345678-abcd', status: 'chart_ready', expires_at: '2026-07-25T10:00:00Z', remaining_questions: 20 }

async function mockApi(page: Page) {
  let reportReady = false
  await page.route('**/api/public/apps/fortune', (route) => route.fulfill({ json: { name: '知命', slug: 'fortune', daily_limit: 3, ttl_hours: 24, max_questions: 20, locations, quota: { remaining: 3, resets_at: '' } } }))
  await page.route('**/api/public/apps/fortune/sessions', (route) => route.fulfill({ status: 201, json: { session, chart, messages: [], quota: { daily_limit: 3, remaining: 2, resets_at: '' } } }))
  await page.route('**/api/public/apps/fortune/sessions/*/report', async (route) => { reportReady = true; await route.fulfill({ contentType: 'text/event-stream', body: `data: ${JSON.stringify({ type: 'run.started', data: {} })}\n\ndata: ${JSON.stringify({ type: 'message.delta', data: { content: '## 格局总论\n命盘显示出稳定而主动的倾向。' } })}\n\ndata: ${JSON.stringify({ type: 'run.completed', data: {} })}\n\n` }) })
  await page.route('**/api/public/apps/fortune/sessions/*', (route) => route.fulfill({ json: { session: { ...session, status: reportReady ? 'report_ready' : 'chart_ready' }, chart, messages: reportReady ? [{ id: 'm1', role: 'assistant', content: '## 格局总论\n命盘显示出稳定而主动的倾向。', created_at: '' }] : [] } }))
}

test('completes the birth form and renders a structured report', async ({ page }) => {
  await mockApi(page)
  await page.goto('/fortune')
  await page.getByLabel('公历出生日期').fill('1998-12-13')
  await page.getByRole('button', { name: '事业' }).click()
  await page.getByRole('button', { name: '开始排盘' }).click()
  await expect(page.getByText('四柱命盘')).toBeVisible()
  await expect(page.getByText('格局总论')).toBeVisible()
  await expect(page.locator('.pillars article')).toHaveCount(4)
  await page.screenshot({ path: 'test-results/fortune-report-desktop.png', fullPage: true })
})

for (const width of [320, 390, 768, 1440]) {
  test(`has no page overflow at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: width < 600 ? 844 : 900 })
    await mockApi(page)
    await page.goto('/fortune')
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
    expect(overflow).toBeLessThanOrEqual(0)
    if (width === 390) await page.screenshot({ path: 'test-results/fortune-form-mobile.png', fullPage: true })
  })
}

test('shows the exhausted quota state without enabling submission', async ({ page }) => {
  await page.route('**/api/public/apps/fortune', (route) => route.fulfill({
    json: {
      name: '知命', slug: 'fortune', daily_limit: 3, ttl_hours: 24, max_questions: 20,
      locations, quota: { remaining: 0, resets_at: '2026-07-27T00:00:00+08:00' },
    },
  }))

  await page.goto('/fortune')

  await expect(page.getByRole('button', { name: '今日额度已用完' })).toBeDisabled()
  await page.screenshot({ path: 'test-results/fortune-quota-exhausted.png', fullPage: true })
})

test('keeps the form usable after a public session error', async ({ page }) => {
  await page.route('**/api/public/apps/fortune', (route) => route.fulfill({
    json: {
      name: '知命', slug: 'fortune', daily_limit: 3, ttl_hours: 24, max_questions: 20,
      locations, quota: { remaining: 3, resets_at: '' },
    },
  }))
  await page.route('**/api/public/apps/fortune/sessions', (route) => route.fulfill({
    status: 429,
    json: { error: { code: 'QUOTA_EXHAUSTED', message: '今日测算额度已用完', details: {} } },
  }))

  await page.goto('/fortune')
  await page.getByLabel('公历出生日期').fill('1998-12-13')
  await page.getByRole('button', { name: '开始排盘' }).click()

  await expect(page.getByText('今日测算额度已用完')).toBeVisible()
  await expect(page.getByRole('button', { name: '开始排盘' })).toBeEnabled()
  await page.screenshot({ path: 'test-results/fortune-public-error.png', fullPage: true })
})

test('redirects the root path to fortune', async ({ page }) => {
  await mockApi(page)

  await page.goto('/')

  await expect(page).toHaveURL(/\/fortune$/)
  await expect(page.getByRole('heading', { name: '出生信息' })).toBeVisible()
})
