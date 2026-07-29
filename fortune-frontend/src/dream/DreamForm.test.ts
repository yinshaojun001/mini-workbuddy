// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import DreamForm from './DreamForm.vue'

const emotions = ['害怕', '焦虑', '平静', '惊奇']

describe('DreamForm', () => {
  it('emits normalized dream payload with selected emotions', async () => {
    const wrapper = mount(DreamForm, { props: { emotions, maxEmotions: 3, remaining: 2, loading: false } })

    await wrapper.get('#dream-text').setValue('  我梦见自己回到旧屋，地面不断积水，怎么也找不到出口。  ')
    await wrapper.findAll('.emotion-grid button')[0].trigger('click')
    await wrapper.findAll('.emotion-grid button')[1].trigger('click')
    await wrapper.get('.dream-check input').setValue(true)
    await wrapper.get('.context-toggle').trigger('click')
    await wrapper.get('#recent-context').setValue('  最近正在考虑搬家。  ')
    await wrapper.get('form').trigger('submit')

    expect(wrapper.emitted('submit')?.[0]).toEqual([{
      dream_text: '我梦见自己回到旧屋，地面不断积水，怎么也找不到出口。',
      emotions: ['害怕', '焦虑'],
      recurring: true,
      recent_context: '最近正在考虑搬家。',
    }])
  })

  it('limits emotion selection and disables submit for short dreams', async () => {
    const wrapper = mount(DreamForm, { props: { emotions, maxEmotions: 3, remaining: 1, loading: false } })
    const buttons = wrapper.findAll('.emotion-grid button')

    await buttons[0].trigger('click')
    await buttons[1].trigger('click')
    await buttons[2].trigger('click')

    expect(buttons[3].attributes('disabled')).toBeDefined()
    expect(wrapper.get('.primary-command').attributes('disabled')).toBeDefined()
  })

  it('enforces text boundaries, keeps recent context optional, and handles exhausted quota', async () => {
    const wrapper = mount(DreamForm, { props: { emotions, maxEmotions: 3, remaining: 1, loading: false } })

    expect(wrapper.find('#recent-context').exists()).toBe(false)
    await wrapper.get('#dream-text').setValue('一'.repeat(20))
    expect(wrapper.get('.primary-command').attributes('disabled')).toBeUndefined()
    expect(wrapper.text()).toContain('20/4000')

    await wrapper.setProps({ remaining: 0, resetsAt: '2026-07-30T00:00:00+08:00' })
    expect(wrapper.get('.primary-command').text()).toBe('今日额度已用完')
    expect(wrapper.get('.primary-command').attributes('disabled')).toBeDefined()
    expect(wrapper.get('.quota-reset').text()).toContain('后恢复')
  })
})
