// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import DreamContext from './DreamContext.vue'

describe('DreamContext', () => {
  it('renders an empty reference match as a normal state', () => {
    const wrapper = mount(DreamContext, {
      props: {
        context: {
          kind: 'dream',
          summary: { emotions: [], recurring: false },
          symbols: [],
          reference_index_version: '1.0.1',
        },
      },
    })

    expect(wrapper.text()).toContain('未命中')
    expect(wrapper.text()).toContain('已记录本次梦境正文')
  })
})
