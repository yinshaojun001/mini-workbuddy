import DOMPurify from 'dompurify'
import MarkdownIt from 'markdown-it'

const parser = new MarkdownIt({ html: false, linkify: true, breaks: true })
export function renderMarkdown(content: string) { return DOMPurify.sanitize(parser.render(content)) }
