// @vitest-environment jsdom

import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import AppsView from './AppsView.vue'

const app = {
  id: 'fortune', name: '知命', slug: 'fortune', agent_id: 'fortune-bazi-agent', enabled: true,
  daily_limit: 3, ttl_hours: 24, max_questions: 20, health: 'model_unavailable',
  public_url: 'https://fortune.inshocking.com/', created_at: '', updated_at: '',
}
const agent = {
  id: 'fortune-bazi-agent', name: '知命八字 Agent', description: '', model_id: 'deepseek-default',
  tool_ids: [], skill_ids: ['bazi-interpreter'], work_directory: '/tmp/fortune', enabled: true,
  is_builtin: true, updated_at: '',
}

function response(value: unknown, status = 200) {
  return new Response(status === 204 ? null : JSON.stringify(value), {
    status,
    headers: { 'content-type': 'application/json' },
  })
}

afterEach(() => vi.unstubAllGlobals())

describe('AppsView', () => {
  it('lists published apps with health and public URL', async () => {
    vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      return response(url === '/api/apps' ? [app] : [agent])
    }))
    const wrapper = mount(AppsView)
    await flushPromises()
    expect(wrapper.text()).toContain('知命')
    expect(wrapper.text()).toContain('模型未就绪')
    expect(wrapper.get('a.public-link').attributes('href')).toBe('https://fortune.inshocking.com/')
  })

  it('creates an app with the selected agent and limits', async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (init?.method === 'POST') return response(app, 201)
      return response(url === '/api/apps' ? [] : [agent])
    })
    vi.stubGlobal('fetch', fetchMock)
    const wrapper = mount(AppsView)
    await flushPromises()
    await wrapper.get('button.button--lime').trigger('click')
    await wrapper.get('#app-name').setValue('知命测试')
    await wrapper.get('#app-slug').setValue('fortune-test')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    const createCall = fetchMock.mock.calls.find(([, init]) => init?.method === 'POST')
    expect(createCall?.[0]).toBe('/api/apps')
    expect(JSON.parse(String(createCall?.[1]?.body))).toMatchObject({
      name: '知命测试', slug: 'fortune-test', agent_id: 'fortune-bazi-agent', daily_limit: 3, ttl_hours: 24,
    })
  })
})
