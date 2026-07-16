import DOMPurify from 'dompurify'
import MarkdownIt from 'markdown-it'

const markdown = new MarkdownIt({
  breaks: true,
  html: true,
  linkify: true,
  typographer: false,
})

markdown.renderer.rules.link_open = (tokens, index, options, _environment, renderer) => {
  const token = tokens[index]
  token.attrSet('target', '_blank')
  token.attrSet('rel', 'noopener noreferrer')
  return renderer.renderToken(tokens, index, options)
}

export function renderMarkdown(source: string): string {
  const rendered = markdown.render(source)
  return DOMPurify.sanitize(rendered, {
    ADD_ATTR: ['target'],
    FORBID_TAGS: ['script', 'style', 'iframe', 'object', 'embed'],
  })
}
