import { describe, expect, it } from 'vitest'
import { extractSseEvents } from './sse'

const first = { run_id: 'r1', sequence: 1, timestamp: '2026-07-15T00:00:00Z', type: 'run.started', data: {} }
const second = { run_id: 'r1', sequence: 2, timestamp: '2026-07-15T00:00:01Z', type: 'message.delta', data: { content: '你好' } }

describe('extractSseEvents', () => {
  it('保留尚未接收完整的尾部事件', () => {
    const input = `data: ${JSON.stringify(first)}\n\ndata: {"run_id":"r1"`
    const result = extractSseEvents(input)
    expect(result.events).toEqual([first])
    expect(result.rest).toBe('data: {"run_id":"r1"')
  })

  it('按顺序解析连续事件', () => {
    const input = `data: ${JSON.stringify(first)}\n\ndata: ${JSON.stringify(second)}\n\n`
    expect(extractSseEvents(input)).toEqual({ events: [first, second], rest: '' })
  })
})

