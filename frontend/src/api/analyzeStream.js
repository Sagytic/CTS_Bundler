import { buildApiUrl } from './client'

export const ANALYZER_STEP_ORDER = ['fetch_data', 'bc', 'fi', 'co', 'mm', 'sd', 'pp', 'architect']

/**
 * POST /api/analyze/ NDJSON stream; updates via callbacks.
 * @param {{ message: string, user_id: string, selected_trs: string[] }} body
 * @param {{
 *   setAnalyzeProgress: (p: { step: string, label: string }) => void,
 *   setAnalyzeCompletedSteps: (fn: (prev: string[]) => string[]) => void,
 *   setAnalyzerResponse: (text: string) => void,
 * }} callbacks
 * @returns {Promise<string | null>} 최종 레포트 마크다운(없으면 null)
 */
export async function streamDeployAnalysis(body, callbacks) {
  const { setAnalyzeProgress, setAnalyzeCompletedSteps, setAnalyzerResponse } = callbacks
  let lastReply = null

  const res = await fetch(buildApiUrl('/api/analyze/'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(res.statusText)

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''
    for (const line of lines) {
      if (!line.trim()) continue
      try {
        const data = JSON.parse(line)
        if (data.done === true && data.reply != null) {
          setAnalyzeCompletedSteps((prev) => [...prev, 'architect'])
          lastReply = data.reply
          setAnalyzerResponse(data.reply)
          break
        }
        if (data.step != null) {
          const cur = data.step || ''
          const curIdx = ANALYZER_STEP_ORDER.indexOf(cur)
          if (curIdx >= 0) {
            setAnalyzeCompletedSteps((prev) => {
              const next = new Set(prev)
              for (let i = 0; i < curIdx; i++) next.add(ANALYZER_STEP_ORDER[i])
              return [...next]
            })
          }
          setAnalyzeProgress({ step: cur, label: data.label || '' })
        }
      } catch {
        /* ignore bad line */
      }
    }
  }

  if (buffer.trim()) {
    try {
      const data = JSON.parse(buffer)
      if (data.done === true && data.reply != null) {
        setAnalyzeCompletedSteps((prev) => [...prev, 'architect'])
        lastReply = data.reply
        setAnalyzerResponse(data.reply)
      }
    } catch {
      /* ignore */
    }
  }

  return lastReply
}
