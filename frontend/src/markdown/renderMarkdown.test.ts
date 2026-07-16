// @vitest-environment jsdom

import { describe, expect, it } from 'vitest'
import { renderMarkdown } from './renderMarkdown'

describe('renderMarkdown', () => {
  it('渲染标题、列表、表格和代码块', () => {
    const html = renderMarkdown(`
## 执行结果

- 第一项
- 第二项

| 名称 | 状态 |
| --- | --- |
| 测试 | 通过 |

\`\`\`python
print("ok")
\`\`\`
`)

    expect(html).toContain('<h2>执行结果</h2>')
    expect(html).toContain('<li>第一项</li>')
    expect(html).toContain('<table>')
    expect(html).toContain('language-python')
  })

  it('清理脚本、事件属性和危险链接', () => {
    const html = renderMarkdown(`
<script>alert('xss')</script>

<img src="x" onerror="alert('xss')">

[危险链接](javascript:alert('xss'))
`)

    expect(html).not.toContain('<script')
    expect(html).not.toContain('onerror')
    expect(html).not.toContain('href="javascript:')
  })

  it('为外部链接增加安全的新窗口属性', () => {
    const html = renderMarkdown('[项目地址](https://github.com/example/project)')

    expect(html).toContain('target="_blank"')
    expect(html).toContain('rel="noopener noreferrer"')
  })
})
