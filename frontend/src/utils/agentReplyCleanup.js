/**
 * 에이전트 답변 후처리 (스트림 완료 후): TR 목록 이중 표기·내부 안내 문구 제거.
 * 백엔드 api/agent_reply_cleanup.py 와 동작을 맞춤.
 */

const LEGACY_HINT =
  /아래는 list_transports 조회 결과입니다\.[\s\S]*?(?=\s*[-*]?\s*[A-Z]{2,4}\d{6,}\s*:)/

const TR_LINE_RE = /^\s*(?:[-*]\s+)?[A-Z]{2,4}\d{6,}\s*:/

function trIdFromLine(line) {
  const m = line.match(/^\s*(?:[-*]\s+)?([A-Z]{2,4}\d{6,})\s*:/)
  return m ? m[1] : null
}

function isTrLine(line) {
  return TR_LINE_RE.test(line)
}

function trIdsFromLines(lines) {
  return lines.map(trIdFromLine).filter(Boolean)
}

function idsEqual(a, b) {
  return a.length === b.length && a.every((v, k) => v === b[k])
}

function normalizeGluedTrHeading(text) {
  return text.replace(/([^\s\n])(###\s*TR\s*목록)/gi, '$1\n\n$2')
}

/**
 * 문자열-aware로 첫 JSON 값 `{...}` 또는 `[...]`의 끝 인덱스까지 파싱 (json.JSONDecoder.raw_decode 대응).
 * @returns {{ value: unknown, end: number } | null}
 */
function rawDecodeFirstJsonValue(s) {
  let i = 0
  while (i < s.length && /\s/.test(s[i])) i += 1
  if (i >= s.length || (s[i] !== '{' && s[i] !== '[')) return null
  const start = i
  const stack = []
  let inStr = false
  let esc = false
  for (; i < s.length; i += 1) {
    const c = s[i]
    if (esc) {
      esc = false
      continue
    }
    if (inStr) {
      if (c === '\\') esc = true
      else if (c === '"') inStr = false
      continue
    }
    if (c === '"') {
      inStr = true
      continue
    }
    if (c === '{') stack.push('}')
    else if (c === '[') stack.push(']')
    else if (c === '}' || c === ']') {
      const expected = stack.pop()
      if (expected !== c) return null
      if (stack.length === 0) {
        const chunk = s.slice(start, i + 1)
        try {
          return { value: JSON.parse(chunk), end: i + 1 }
        } catch {
          return null
        }
      }
    }
  }
  return null
}

/** Docs MCP search 등 `{"results":[...]}` 가 답변 앞에 붙은 경우 제거 */
function stripLeadingSearchResultsJsonBlob(text) {
  if (!text || !text.includes('results')) return text
  const s = text.replace(/^\uFEFF/, '').trimStart()
  const parsed = rawDecodeFirstJsonValue(s)
  if (!parsed) return text
  const { value, end } = parsed
  if (!value || typeof value !== 'object' || !Array.isArray(value.results)) return text
  const { results } = value
  if (results.length > 0) {
    const sample = results[0]
    if (!sample || typeof sample !== 'object') return text
    const keys = ['title', 'url', 'snippet', 'id', 'topic', 'library_id']
    if (!keys.some((k) => Object.prototype.hasOwnProperty.call(sample, k))) return text
  }
  return s.slice(end).replace(/^\s+/, '')
}

function stripLegacyListTransportsHint(text) {
  if (!text || !text.includes('아래는 list_transports')) return text
  return text.replace(LEGACY_HINT, '')
}

function dedupeByTrailingTrLines(beforeRaw, after, afterTr) {
  const beforeLines = beforeRaw.split('\n')
  const trTail = []
  let cut = beforeLines.length
  let i = beforeLines.length - 1
  while (i >= 0) {
    const line = beforeLines[i]
    if (line.trim() === '') {
      if (trTail.length) break
      cut = i
      i -= 1
      continue
    }
    if (isTrLine(line)) {
      trTail.unshift(line)
      cut = i
      i -= 1
      continue
    }
    break
  }
  if (!trTail.length || !idsEqual(trIdsFromLines(trTail), trIdsFromLines(afterTr))) return null
  const newBefore = beforeLines.slice(0, cut).join('\n').replace(/\s+$/, '')
  const sep = newBefore ? '\n\n' : ''
  return `${newBefore}${sep}${after}`
}

function allLinesMatchTr(lines) {
  const nonEmpty = lines.filter((ln) => ln.trim())
  return nonEmpty.length > 0 && nonEmpty.every((ln) => TR_LINE_RE.test(ln))
}

function dedupeByParagraph(beforeRaw, after, afterIds) {
  const t = beforeRaw.trim()
  if (!t) return null
  const paras = t.split(/\n\s*\n+/)
  for (let pi = paras.length - 1; pi >= 0; pi -= 1) {
    const p = paras[pi].trim()
    if (!p) continue
    const lines = p.split('\n')
    if (!allLinesMatchTr(lines)) continue
    if (!idsEqual(trIdsFromLines(lines), afterIds)) continue
    const newParas = paras.filter((_, i) => i !== pi)
    const newBefore = newParas.map((x) => x.trim()).filter(Boolean).join('\n\n').replace(/\s+$/, '')
    const sep = newBefore ? '\n\n' : ''
    return `${newBefore}${sep}${after}`
  }
  return null
}

function dedupeBySlidingWindow(beforeRaw, after, afterTr) {
  const beforeLines = beforeRaw.split('\n')
  const n = afterTr.length
  const afterIds = trIdsFromLines(afterTr)
  if (n === 0 || beforeLines.length < n) return null
  for (let s = 0; s <= beforeLines.length - n; s += 1) {
    const chunk = beforeLines.slice(s, s + n)
    if (!chunk.every((ln) => isTrLine(ln))) continue
    if (!idsEqual(trIdsFromLines(chunk), afterIds)) continue
    const newLines = [...beforeLines.slice(0, s), ...beforeLines.slice(s + n)]
    const newBefore = newLines.join('\n').replace(/\s+$/, '')
    const sep = newBefore ? '\n\n' : ''
    return `${newBefore}${sep}${after}`
  }
  return null
}

function dedupeTrBlockBeforeTrHeading(text) {
  const m = text.match(/###\s*TR\s*목록/i)
  if (!m || m.index === undefined) return text
  const idx = m.index
  const beforeRaw = text.slice(0, idx)
  let after = text.slice(idx).trimStart()

  const afterLines = after.split('\n')
  const afterTr = []
  let j = 1
  while (j < afterLines.length) {
    const line = afterLines[j]
    if (isTrLine(line)) {
      afterTr.push(line)
      j += 1
      continue
    }
    if (line.trim() === '' && afterTr.length) break
    if (afterTr.length) break
    j += 1
  }

  if (!afterTr.length) return text
  const afterIds = trIdsFromLines(afterTr)

  return (
    dedupeByTrailingTrLines(beforeRaw, after, afterTr) ||
    dedupeByParagraph(beforeRaw, after, afterIds) ||
    dedupeBySlidingWindow(beforeRaw, after, afterTr) ||
    text
  )
}

/**
 * @param {string} text
 * @returns {string}
 */
export function cleanAgentReplyText(text) {
  if (!text) return text
  let t = stripLeadingSearchResultsJsonBlob(text)
  t = normalizeGluedTrHeading(t)
  t = stripLegacyListTransportsHint(t)
  t = dedupeTrBlockBeforeTrHeading(t)
  return t.trim()
}
