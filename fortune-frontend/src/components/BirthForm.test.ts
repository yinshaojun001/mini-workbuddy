// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import BirthForm from './BirthForm.vue'

const locations = [
  { code: '110000', parent_code: 'CN', name: '北京市', level: 'province' as const },
  { code: '110100', parent_code: '110000', name: '北京市', level: 'city' as const },
]
describe('BirthForm', () => {
  it('disables time and true solar time when birth time is unknown', async () => {
    const wrapper = mount(BirthForm, { props: { locations, remaining: 3, loading: false } })
    const unknown = wrapper.get('.checkline input')
    await unknown.setValue(true)
    expect(wrapper.get('input[type="time"]').attributes('disabled')).toBeDefined()
    expect(wrapper.get('.toggleline input').attributes('disabled')).toBeDefined()
  })
})
