// @vitest-environment jsdom
import { mount, flushPromises } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { DreamMetadata, DreamSessionPayload } from '@/types'

const api = vi.hoisted(() => ({
  getMetadata: vi.fn(),
  createSession: vi.fn(),
  getSession: vi.fn(),
  deleteSession: vi.fn(),
  streamRun: vi.fn(),
}))

vi.mock('@/runtime/api', () => api)

const metadata: DreamMetadata = {
  name: '知梦',
  slug: 'dream',
  daily_limit: 3,
  ttl_hours: 24,
  max_questions: 20,
  quota: { remaining: 3, resets_at: '' },
  form: {
    dream_text: { min_length: 20, max_length: 4000 },
    emotions: { options: ['焦虑', '怀念', '平静'], max_items: 3 },
    recent_context: { max_length: 500 },
    recurring: { type: 'boolean', default: false },
  },
}

const created: DreamSessionPayload = {
  session: { id: 'dream-session-1234', status: 'context_ready', expires_at: '2026-07-30T10:00:00Z', remaining_questions: 20 },
  quota: { daily_limit: 3, remaining: 2, resets_at: '' },
  context: {
    kind: 'dream',
    summary: { emotions: ['焦虑'], recurring: false },
    symbols: [{ id: 'house', label: '房屋' }],
    reference_index_version: '1.0.0',
  },
  messages: [],
}

const restored: DreamSessionPayload = {
  ...created,
  session: { ...created.session, status: 'report_ready' },
  messages: [{ id: 'm1', role: 'assistant', content: '## 梦境速写\n旧屋和积水可以先看作压力与过渡的象征。', created_at: '' }],
}

describe('DreamView', () => {
  beforeEach(() => {
    vi.resetModules()
    vi.clearAllMocks()
    const values = new Map<string, string>()
    vi.stubGlobal('localStorage', {
      getItem: (key: string) => values.get(key) ?? null,
      setItem: (key: string, value: string) => values.set(key, value),
      removeItem: (key: string) => values.delete(key),
    })
    api.getMetadata.mockResolvedValue({ ...metadata, quota: { ...metadata.quota } })
    api.createSession.mockResolvedValue(created)
    api.getSession.mockResolvedValue(restored)
    api.streamRun.mockImplementation(async (_slug, _id, _mode, _content, onEvent) => {
      onEvent({ type: 'message.delta', data: { content: '## 梦境速写\n旧屋和积水可以先看作压力与过渡的象征。' } })
      onEvent({ type: 'run.completed', data: {} })
    })
  })

  it('creates a dream session and renders the streamed report', async () => {
    const DreamView = (await import('./DreamView.vue')).default
    const wrapper = mount(DreamView, {
      global: { stubs: { RouterLink: { template: '<a><slot /></a>' } } },
    })

    await flushPromises()
    await wrapper.get('#dream-text').setValue('我梦见自己回到旧屋，地面不断积水，怎么也找不到出口。')
    await wrapper.findAll('.emotion-grid button')[0].trigger('click')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(api.createSession).toHaveBeenCalledWith('dream', {
      dream_text: '我梦见自己回到旧屋，地面不断积水，怎么也找不到出口。',
      emotions: ['焦虑'],
      recurring: false,
      recent_context: null,
    })
    expect(api.streamRun).toHaveBeenCalledWith('dream', 'dream-session-1234', 'report', undefined, expect.any(Function))
    expect(wrapper.text()).toContain('房屋')
    expect(wrapper.text()).toContain('梦境速写')
  })
})
