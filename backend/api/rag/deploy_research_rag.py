"""
배포 심의 LangGraph 전용 CRAG 라이트.

- Chroma `retrieve`로 1차 검색
- (선택) 소형 LLM으로 관련성 판단 → 불충분 시 `rewritten_query`로 1회 재검색
- 모듈 전문가·아키텍트 프롬프트에 주입할 텍스트 블록 반환
"""
from __future__ import annotations

import json
import logging
from typing import Any

_log = logging.getLogger("cts.ai")


def tr_objects_snippet(sap_data_raw: list, max_objs: int = 40) -> str:
    """TR 목록에서 오브젝트 타입:이름 문자열을 모아 검색 쿼리 보강."""
    names: list[str] = []
    for tr in sap_data_raw or []:
        objects = tr.get("objects") or tr.get("OBJECTS") or []
        for o in objects:
            t = str(o.get("OBJECT", o.get("object", "")))
            n = str(o.get("OBJ_NAME", o.get("obj_name", "")))
            if n:
                names.append(f"{t}:{n}")
            if len(names) >= max_objs:
                return ", ".join(names)
    return ", ".join(names)


def build_initial_query(user_input: str, sap_data_raw: list) -> str:
    ui = (user_input or "").strip()
    snip = tr_objects_snippet(sap_data_raw)
    parts: list[str] = []
    if ui:
        parts.append(ui)
    if snip:
        parts.append(f"변경 오브젝트: {snip}")
    if not parts:
        return "SAP CTS TR 배포 심의 종속성 티켓 요구사항"
    return "\n".join(parts)


def _format_docs(results: list[tuple[Any, float]]) -> str:
    lines: list[str] = []
    for i, (doc, score) in enumerate(results, 1):
        pc = getattr(doc, "page_content", "") or ""
        meta = getattr(doc, "metadata", None) or {}
        src = meta.get("source", "")
        lines.append(
            f"--- 문서{i} (source={src}, score={float(score):.4f}) ---\n{pc[:2500]}"
        )
    return "\n\n".join(lines)


def crag_retrieve_for_deploy_review(
    *,
    query: str,
    k: int,
    llm_fast: Any | None,
    user_input: str,
    sap_data_raw: list,
) -> tuple[str, dict[str, Any]]:
    """
    Returns:
        (research_context_block, metadata for state['research_meta'])
    """
    from api.rag.services import retrieve

    meta: dict[str, Any] = {"rounds": [], "final_query": query}
    if not (query or "").strip():
        return "", {**meta, "skip": "empty_query"}

    try:
        batch1 = retrieve(query.strip(), k=k)
    except Exception as e:
        _log.warning("deploy_research_rag retrieve failed: %s", e)
        return "", {**meta, "error": str(e)}

    meta["rounds"].append({"query": query.strip(), "n_hits": len(batch1)})

    if not batch1:
        msg = (
            "(내부 RAG 인덱스에 매칭된 문서가 없습니다. "
            "`POST /api/rag/ingest/` 로 종속성·티켓 데이터를 적재했는지 확인하세요.)"
        )
        return msg, {**meta, "empty": True}

    batch_final = batch1

    if llm_fast is not None:
        try:
            from langchain_core.prompts import ChatPromptTemplate
            from pydantic import BaseModel, Field

            class _Judgment(BaseModel):
                relevant: bool = Field(
                    description="검색 청크가 이 배포 심의(사용자 요청+TR)에 실질적 근거로 쓸 만한가"
                )
                reason: str = Field(description="한두 문장 이유")
                rewritten_query: str = Field(
                    default="",
                    description="relevant가 false일 때만, 더 나은 검색을 위한 짧은 쿼리. true면 빈 문자열.",
                )

            tr_slice = (sap_data_raw or [])[:4]
            tr_json = json.dumps(tr_slice, ensure_ascii=False)[:4500]
            doc_summaries = "\n".join(
                f"[{i + 1}] {(getattr(d, 'page_content', '') or '')[:600]}"
                for i, (d, _) in enumerate(batch1[: max(k, 3)])
            )
            prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        "당신은 RAG 검색 품질 심사자입니다. "
                        "청크가 종속성·티켓·TR 맥락에 도움이 되면 relevant=true. "
                        "전혀 무관하면 false와 검색어 rewritten_query(한국어 가능).",
                    ),
                    (
                        "human",
                        "사용자 요청:\n{user_input}\n\nTR 일부(JSON):\n{tr_json}\n\n검색 청크:\n{docs}",
                    ),
                ]
            )
            structured = llm_fast.with_structured_output(_Judgment)
            j = (prompt | structured).invoke(
                {
                    "user_input": (user_input or "(없음)")[:2000],
                    "tr_json": tr_json,
                    "docs": doc_summaries,
                }
            )
            meta["judgment"] = j.model_dump()
            if not j.relevant and (j.rewritten_query or "").strip():
                q2 = (j.rewritten_query or "").strip()[:500]
                try:
                    batch2 = retrieve(q2, k=k)
                    meta["rounds"].append({"query": q2, "n_hits": len(batch2)})
                    if batch2:
                        batch_final = batch2
                        meta["final_query"] = q2
                except Exception as e2:
                    meta["rewrite_retrieve_error"] = str(e2)
        except Exception as e:
            _log.warning("deploy_research_rag judgment/rewrite skipped: %s", e)
            meta["judgment_error"] = str(e)

    body = _format_docs(batch_final)
    header = (
        f"[Researcher / CRAG] 검색 쿼리: `{meta.get('final_query', query)}` | "
        f"선택 문서 수: {len(batch_final)}\n\n"
    )
    return header + body, meta
