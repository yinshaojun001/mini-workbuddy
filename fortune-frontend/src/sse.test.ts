import { describe, expect, it } from 'vitest'
import { consumeSse } from './sse'

describe('consumeSse', () => {
  it('parses events split across chunks and accepts CRLF framing', async () => {
    const encoder = new TextEncoder()
    const stream = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(encoder.encode('data: {"type":"message.'))
        controller.enqueue(encoder.encode('delta","data":{"content":"命"}}\r\n\r\n'))
        controller.enqueue(encoder.encode('data: {"type":"run.completed","data":{}}'))
        controller.close()
      },
    })
    const events: Array<{ type: string }> = []

    await consumeSse(stream, (event) => events.push(event))

    expect(events.map((event) => event.type)).toEqual(['message.delta', 'run.completed'])
  })
})
