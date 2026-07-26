// @vitest-environment jsdom
import { describe, expect, it } from 'vitest'
import { renderMarkdown } from './markdown'
describe('renderMarkdown', () => {
  it('renders report sections and removes executable markup', () => {
    const html = renderMarkdown('## 格局总论\n<script>alert(1)</script>\n建议保持节奏。')
    expect(html).toContain('<h2>格局总论</h2>')
    expect(html).not.toContain('<script')
  })
})
