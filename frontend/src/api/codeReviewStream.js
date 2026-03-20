import { buildApiUrl } from './client'

/**
 * POST /api/code-review/ with stream:true — plain text UTF-8 chunks (LLM 토큰 스트림).
 * @param {object} payload objName, trkorr, abapCode, requirementSpec
 * @param {{ onDelta: (fullText: string) => void, signal?: AbortSignal }} opts
 * @returns {Promise<string>} 최종 전체 텍스트
 */
export async function streamCodeReview(payload, { onDelta, signal }) {
  const res = await fetch(buildApiUrl('/api/code-review/'), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      // DRF APIView는 초기 콘텐츠 협상에 renderer가 필요함. text/plain만내면 JSONRenderer와 불일치 → 406
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
    onDelta(t)
    return t
  }

  const decoder = new TextDecoder()
  let acc = ''
  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    acc += decoder.decode(value, { stream: true })
    onDelta(acc)
  }
  acc += decoder.decode()
  if (acc) onDelta(acc)
  return acc
}
