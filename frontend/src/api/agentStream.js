import { buildApiUrl } from './client'
import { cleanAgentReplyText } from '../utils/agentReplyCleanup'

/**
 * POST /api/agent/ with stream:true — UTF-8 텍스트 청크 + 마지막에 \x1e + JSON 메타(steps, react_used_tools).
 * @param {object} payload message, include_steps
 * @param {{ onDelta: (displayText: string) => void, signal?: AbortSignal }} opts
 * @returns {Promise<{ reply: string, steps: array, react_used_tools: number, error?: string }>}
 */
export async function streamAgentChat(payload, { onDelta, signal }) {
  const res = await fetch(buildApiUrl('/api/agent/'), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json, text/plain; q=0.9, */*; q=0.8',
    },
    body: JSON.stringify({ ...payload, stream: true }),
    signal,
  })

  if (!res.ok) {
    const errText = await res.text()
    throw new Error((errText || `HTTP ${res.status}`).slice(0, 800))
  }

  const reader = res.body?.getReader()
  if (!reader) {
    const t = await res.text()
    const parsed = splitAgentStreamBody(t)
    onDelta(parsed.reply)
    return parsed
  }

  const decoder = new TextDecoder()
  let acc = ''
  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    acc += decoder.decode(value, { stream: true })
    onDelta(displayWithoutMeta(acc))
  }
  acc += decoder.decode()
  const parsed = splitAgentStreamBody(acc)
  onDelta(parsed.reply)
  return parsed
}

function displayWithoutMeta(raw) {
  const i = raw.indexOf('\x1e')
  return i < 0 ? raw : raw.slice(0, i)
}

function splitAgentStreamBody(raw) {
  const i = raw.indexOf('\x1e')
  const replyRaw = i < 0 ? raw : raw.slice(0, i)
  const reply = cleanAgentReplyText(replyRaw)
  let steps = []
  let react_used_tools = 0
  let error
  if (i >= 0) {
    try {
      const meta = JSON.parse(raw.slice(i + 1))
      steps = meta.steps || []
      react_used_tools = meta.react_used_tools ?? 0
      error = meta.error
    } catch {
      // ignore malformed trailer
    }
  }
  return { reply, steps, react_used_tools, error }
}
