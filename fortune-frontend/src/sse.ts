import type { SseEvent } from './types'

export async function consumeSse(
  body: ReadableStream<Uint8Array>,
  onEvent: (event: SseEvent) => void,
): Promise<void> {
  const reader = body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { value, done } = await reader.read()
    buffer += decoder.decode(value, { stream: !done }).replace(/\r\n/g, '\n')
    const chunks = buffer.split('\n\n')
    buffer = chunks.pop() || ''
    for (const chunk of chunks) emitChunk(chunk, onEvent)
    if (done) break
  }

  if (buffer.trim()) emitChunk(buffer, onEvent)
}

function emitChunk(chunk: string, onEvent: (event: SseEvent) => void): void {
  const data = chunk
    .split('\n')
    .filter((line) => line.startsWith('data:'))
    .map((line) => line.slice(5).trimStart())
    .join('\n')
  if (data) onEvent(JSON.parse(data) as SseEvent)
}
