import type { RunEvent } from '@/types'

export function extractSseEvents(input: string): { events: RunEvent[]; rest: string } {
  const chunks = input.split('\n\n')
  const rest = chunks.pop() || ''
  const events: RunEvent[] = []
  for (const chunk of chunks) {
    const data = chunk
      .split('\n')
      .filter(line => line.startsWith('data: '))
      .map(line => line.slice(6))
      .join('\n')
    if (data) events.push(JSON.parse(data) as RunEvent)
  }
  return { events, rest }
}

