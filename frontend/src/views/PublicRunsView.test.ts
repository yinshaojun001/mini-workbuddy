// @vitest-environment jsdom
import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import PublicRunsView from './PublicRunsView.vue'
import { ApiRequestError, deletePublicRun, getPublicRun, getPublicRunStats, listPublicRuns } from '@/api/client'

vi.mock('@/api/client', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/api/client')>()),
  listPublicRuns: vi.fn(), getPublicRun: vi.fn(), getPublicRunStats: vi.fn(), deletePublicRun: vi.fn(),
}))

const session = {
  session_id: '00000000-0000-4000-8000-000000000001', app_id: 'fortune', app_name: '知命',
  status: 'active' as const, created_at: '2026-07-26T10:00:00Z', updated_at: '2026-07-26T10:01:00Z',
  expires_at: '2026-07-27T10:00:00Z', remaining_questions: 2, message_count: 1, run_count: 1,
  last_run_status: 'completed' as const,
}
const stats = { apps: { fortune: { sessions_created: 1, runs_completed: 1, reports_failed: 0, questions_failed: 0, average_duration_ms: 50 } }, total: { sessions_created: 1, runs_completed: 1, reports_failed: 0, questions_failed: 0, average_duration_ms: 50 } }
const maskedBirth = { name: '张*', birth_date: '****-**-**' }
const chartSummary = { pillars: { year: { gan_zhi: '戊寅' } }, day_master: { gan: '乙' } }
const detail = { session, input: { kind: 'fortune', fields: maskedBirth }, context: { kind: 'fortune', summary: chartSummary }, birth: maskedBirth, chart: chartSummary, messages: [{ id: 'm1', role: 'assistant', content: '已脱敏', created_at: 'now' }], runs: [], events: [], historical_events_unavailable: false }
const dreamSession = { ...session, session_id: '00000000-0000-4000-8000-000000000012', app_id: 'dream', app_name: '知梦' }
const dreamDetail = { session: dreamSession, input: { kind: 'dream', fields: { emotions: ['焦虑'], recurring: true, dream_length: 42, has_recent_context: true } }, context: { kind: 'dream', summary: { symbols: [{ id: 'house', label: '房屋' }, { id: 'water', label: '水' }] } }, messages: [], runs: [], events: [], historical_events_unavailable: false }

describe('PublicRunsView', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.mocked(listPublicRuns).mockResolvedValue({ items: [session], next_cursor: null, refreshed_at: 'now' })
    vi.mocked(getPublicRunStats).mockResolvedValue(stats as never)
    vi.mocked(getPublicRun).mockImplementation(async (_id, sensitive) => sensitive ? { ...detail, input: { kind: 'fortune', fields: { ...maskedBirth, name: '张三', birth_date: '1998-12-13' } }, birth: { ...maskedBirth, name: '张三', birth_date: '1998-12-13' } } as never : detail as never)
    vi.mocked(deletePublicRun).mockResolvedValue(undefined)
    vi.stubGlobal('confirm', vi.fn(() => true))
  })
  afterEach(() => { vi.useRealTimers(); vi.restoreAllMocks() })

  it('loads overview and polls list and stats every 15 seconds', async () => {
    const wrapper = mount(PublicRunsView)
    await flushPromises()
    expect(wrapper.text()).toContain('累计匿名会话')
    expect(wrapper.text()).toContain(session.session_id)
    const before = vi.mocked(listPublicRuns).mock.calls.length
    await vi.advanceTimersByTimeAsync(15_000)
    await flushPromises()
    expect(vi.mocked(listPublicRuns).mock.calls.length).toBeGreaterThan(before)
    wrapper.unmount()
    const after = vi.mocked(listPublicRuns).mock.calls.length
    await vi.advanceTimersByTimeAsync(15_000)
    expect(vi.mocked(listPublicRuns).mock.calls.length).toBe(after)
  })

  it('reveals sensitive data explicitly and resets it after closing the drawer', async () => {
    const wrapper = mount(PublicRunsView)
    await flushPromises()
    await wrapper.find('tbody tr').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('张*')
    await wrapper.find('.public-birth .button').trigger('click')
    await flushPromises()
    expect(vi.mocked(getPublicRun)).toHaveBeenCalledWith(session.session_id, true)
    expect(wrapper.text()).toContain('张三')
    await wrapper.find('.public-drawer > header .icon-button').trigger('click')
    await wrapper.find('tbody tr').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('张*')
    expect(wrapper.text()).not.toContain('张三')
  })

  it('confirms deletion with the no-refund warning', async () => {
    const wrapper = mount(PublicRunsView)
    await flushPromises()
    await wrapper.find('tbody tr').trigger('click')
    await flushPromises()
    await wrapper.find('.public-drawer > footer .button--danger').trigger('click')
    await flushPromises()
    expect(confirm).toHaveBeenCalledWith(expect.stringContaining('不会返还已消耗额度'))
    expect(deletePublicRun).toHaveBeenCalledWith(session.session_id)
  })

  it('shows a permanently redacted dream summary without a reveal action', async () => {
    vi.mocked(listPublicRuns).mockResolvedValueOnce({ items: [dreamSession], next_cursor: null, refreshed_at: 'now' })
    vi.mocked(getPublicRun).mockResolvedValue(dreamDetail as never)
    const wrapper = mount(PublicRunsView)
    await flushPromises()
    await wrapper.find('tbody tr').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('梦境摘要')
    expect(wrapper.text()).toContain('焦虑')
    expect(wrapper.text()).toContain('房屋')
    expect(wrapper.text()).toContain('水')
    expect(wrapper.text()).not.toContain('显示敏感资料')
    expect(wrapper.find('.public-birth .button').exists()).toBe(false)
  })

  it('keeps existing rows when automatic refresh fails', async () => {
    const wrapper = mount(PublicRunsView)
    await flushPromises()
    vi.mocked(listPublicRuns).mockRejectedValueOnce(new Error('temporary outage'))

    await vi.advanceTimersByTimeAsync(15_000)
    await flushPromises()

    expect(wrapper.text()).toContain(session.session_id)
    expect(wrapper.text()).toContain('自动刷新失败')
  })

  it('keeps the drawer open when deletion is rejected for a running session', async () => {
    vi.mocked(deletePublicRun).mockRejectedValueOnce(
      new ApiRequestError(409, 'SESSION_RUNNING', 'running'),
    )
    const wrapper = mount(PublicRunsView)
    await flushPromises()
    await wrapper.find('tbody tr').trigger('click')
    await flushPromises()

    await wrapper.find('.public-drawer > footer .button--danger').trigger('click')
    await flushPromises()

    expect(wrapper.find('.public-drawer').exists()).toBe(true)
    expect(wrapper.text()).toContain('当前运行结束后才能删除会话')
  })

  it('refreshes open detail manually and closes it with Escape', async () => {
    const wrapper = mount(PublicRunsView)
    await flushPromises()
    await wrapper.find('tbody tr').trigger('click')
    await flushPromises()
    const before = vi.mocked(getPublicRun).mock.calls.length

    await wrapper.find('.public-runs-heading .icon-button').trigger('click')
    await flushPromises()
    expect(vi.mocked(getPublicRun).mock.calls.length).toBeGreaterThan(before)

    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    await flushPromises()
    expect(wrapper.find('.public-drawer').exists()).toBe(false)
  })
})
