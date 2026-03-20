"""
에이전트 최종 답변 후처리: TR 목록 중복·내부 안내 문구 유출 제거.
"""
from __future__ import annotations

import json
import re

_HEADING_TR = re.compile(r"###\s*TR\s*목록", re.IGNORECASE)
# 과거 list_transports에 넣었던 사용자 노출용 안내(첫 TR 라인 직전까지)
_LEGACY_HINT = re.compile(
    r"아래는 list_transports 조회 결과입니다\.[\s\S]*?(?=\s*[-*]?\s*[A-Z]{2,4}\d{6,}\s*:)",
)


def strip_legacy_list_transports_hint(text: str) -> str:
    """모델이 도구 안내 문구를 답변에 그대로 붙인 경우 제거."""
    if not text or "아래는 list_transports" not in text:
        return text
    return _LEGACY_HINT.sub("", text, count=1)


def _tr_ids_from_line_block(lines: list[str]) -> list[str]:
    ids: list[str] = []
    for line in lines:
        m = re.match(r"^\s*(?:[-*]\s+)?([A-Z]{2,4}\d{6,})\s*:", line)
        if m:
            ids.append(m.group(1))
    return ids


_TR_LINE_RE = re.compile(r"^\s*(?:[-*]\s+)?[A-Z]{2,4}\d{6,}\s*:")


def _all_lines_match_tr(lines: list[str]) -> bool:
    non_empty = [ln for ln in lines if ln.strip()]
    return bool(non_empty) and all(_TR_LINE_RE.match(ln) for ln in non_empty)


def _dedupe_by_trailing_tr_lines(before_raw: str, after: str, after_tr: list[str]) -> str | None:
    """`before` 끝이 TR 줄들로만 끝나면 그 블록 제거. 실패 시 None."""
    before_lines = before_raw.split("\n")
    tr_tail: list[str] = []
    cut = len(before_lines)
    i = len(before_lines) - 1
    while i >= 0:
        line = before_lines[i]
        if line.strip() == "":
            if tr_tail:
                break
            cut = i
            i -= 1
            continue
        if _TR_LINE_RE.match(line):
            tr_tail.insert(0, line)
            cut = i
            i -= 1
            continue
        break
    if not tr_tail or _tr_ids_from_line_block(tr_tail) != _tr_ids_from_line_block(
        after_tr
    ):
        return None
    new_before = "\n".join(before_lines[:cut]).rstrip()
    sep = "\n\n" if new_before else ""
    return f"{new_before}{sep}{after}"


def _dedupe_by_tr_paragraph(before_raw: str, after: str, after_ids: list[str]) -> str | None:
    """
    빈 줄로 구분된 문단 중, 전 줄이 TR 형식이고 TR id 순서가 헤딩 아래와 동일한 문단을
    뒤에서부터 찾아 제거 (티켓/종속성 문단이 그 뒤에 있을 때).
    """
    if not before_raw.strip():
        return None
    paras = re.split(r"(?:\r?\n\s*){2,}", before_raw.strip())
    if len(paras) < 1:
        return None
    for pi in range(len(paras) - 1, -1, -1):
        p = paras[pi].strip()
        if not p:
            continue
        lines = p.split("\n")
        if not _all_lines_match_tr(lines):
            continue
        if _tr_ids_from_line_block(lines) != after_ids:
            continue
        new_paras = [x for i, x in enumerate(paras) if i != pi]
        new_before = "\n\n".join(x.strip() for x in new_paras if x.strip()).rstrip()
        sep = "\n\n" if new_before else ""
        return f"{new_before}{sep}{after}"
    return None


def _dedupe_by_sliding_window(before_raw: str, after: str, after_tr: list[str]) -> str | None:
    """연속 n줄이 모두 TR이고 id 순서가 헤딩 아래와 같으면 해당 구간 삭제 (문단 구분 없을 때)."""
    before_lines = before_raw.split("\n")
    n = len(after_tr)
    if n == 0 or len(before_lines) < n:
        return None
    after_ids = _tr_ids_from_line_block(after_tr)
    for s in range(0, len(before_lines) - n + 1):
        chunk = before_lines[s : s + n]
        if not all(_TR_LINE_RE.match(ln) for ln in chunk):
            continue
        if _tr_ids_from_line_block(chunk) != after_ids:
            continue
        new_lines = before_lines[:s] + before_lines[s + n :]
        new_before = "\n".join(new_lines).rstrip()
        sep = "\n\n" if new_before else ""
        return f"{new_before}{sep}{after}"
    return None


def dedupe_tr_block_before_tr_heading(text: str) -> str:
    """
    '### TR 목록' 아래 TR 목록과 동일한 TR 블록이 헤딩 앞에 있으면 한쪽 제거.
    """
    if not text or "###" not in text:
        return text
    m = _HEADING_TR.search(text)
    if not m:
        return text
    idx = m.start()
    before_raw = text[:idx]
    after = text[idx:].lstrip()

    after_lines = after.split("\n")
    if not after_lines:
        return text
    after_tr: list[str] = []
    j = 1
    while j < len(after_lines):
        line = after_lines[j]
        if _TR_LINE_RE.match(line):
            after_tr.append(line)
            j += 1
            continue
        if line.strip() == "" and after_tr:
            break
        if after_tr:
            break
        j += 1

    if not after_tr:
        return text

    after_ids = _tr_ids_from_line_block(after_tr)

    out = _dedupe_by_trailing_tr_lines(before_raw, after, after_tr)
    if out is not None:
        return out
    out = _dedupe_by_tr_paragraph(before_raw, after, after_ids)
    if out is not None:
        return out
    out = _dedupe_by_sliding_window(before_raw, after, after_tr)
    if out is not None:
        return out
    return text


def normalize_glued_tr_heading(text: str) -> str:
    """'없음### TR 목록' 처럼 붙은 헤딩 앞에 줄바꿈 삽입."""
    return re.sub(
        r"([^\s\n])(###\s*TR\s*목록)",
        r"\1\n\n\2",
        text,
        flags=re.IGNORECASE,
    )


def strip_leading_search_results_json_blob(text: str) -> str:
    """Docs MCP 등 `search`가 반환한 {\"results\":[...]} 원문이 답변 앞(또는 공백 뒤)에 붙은 경우 제거."""
    if not text or "results" not in text:
        return text
    s = text.lstrip()
    if not s.startswith("{"):
        return text
    dec = json.JSONDecoder()
    try:
        obj, end = dec.raw_decode(s)
    except json.JSONDecodeError:
        return text
    if not isinstance(obj, dict):
        return text
    results = obj.get("results")
    if not isinstance(results, list):
        return text
    if results:
        sample = results[0]
        if not isinstance(sample, dict):
            return text
        if not any(
            k in sample for k in ("title", "url", "snippet", "id", "topic", "library_id")
        ):
            return text
    return s[end:].lstrip()


def clean_agent_reply_text(text: str) -> str:
    """스트림/비스트림 공통 후처리."""
    if not text:
        return text
    t = strip_leading_search_results_json_blob(text)
    t = normalize_glued_tr_heading(t)
    t = strip_legacy_list_transports_hint(t)
    t = dedupe_tr_block_before_tr_heading(t)
    return t.strip()
