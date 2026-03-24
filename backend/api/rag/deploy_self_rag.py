"""
배포 심의 LangGraph 2단계: Self-RAG (최종 보고서 근거 검증·1회 보정).

아키텍트가 생성한 `final_report`를 fast LLM으로 심사하고,
내부 RAG·TR 데이터에 비추어 근거 없는 주장이 있으면 동일 맥락에서 1회 재작성합니다.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

_log = logging.getLogger("cts.ai")


def substantive_graph(graph_meta: dict | None) -> bool:
    """GraphRAG로 수집한 간선이 있는지."""
    if not graph_meta or graph_meta.get("skipped"):
        return False
    return int(graph_meta.get("edge_count") or 0) > 0


def substantive_research(research_meta: dict, research_context: str) -> bool:
    """Chroma hit이 있었는지 등, 심사 시 내부 KB를 실질 근거로 쓸 수 있는지."""
    if not research_meta:
        return False
    if research_meta.get("empty") or research_meta.get("skip") == "empty_query":
        return False
    for r in research_meta.get("rounds") or []:
        if int(r.get("n_hits") or 0) > 0:
            return True
    rc = (research_context or "").strip()
    if "--- 문서" in rc and len(rc) > 400:
        return True
    return False


class _GroundingJudge(BaseModel):
    is_grounded: bool = Field(
        description="구체적 사실·티켓·오브젝트·종속성 주장이 아래 근거(TR·내부KB)와 모순 없이 수용 가능한가"
    )
    issues: list[str] = Field(
        default_factory=list,
        description="근거 없음·과장·내부KB/TR과 모순되는 문장 요지, 각 1줄, 최대 8개",
    )
    severity: str = Field(
        description="none | minor | major — major이거나 is_grounded=false면 보정 권장"
    )


def review_deploy_final_report(
    *,
    final_report: str,
    research_context: str,
    research_meta: dict,
    graph_context: str = "",
    graph_meta: dict | None = None,
    sap_data_raw: list,
    user_input: str,
    llm_fast: Any,
) -> tuple[str, dict[str, Any]]:
    """
    Returns:
        (report_after_maybe_revision, metadata for state['self_rag_meta'])
    """
    gmeta = graph_meta if graph_meta is not None else {}
    meta: dict[str, Any] = {
        "skipped": False,
        "revised": False,
        "had_substantive_rag": substantive_research(research_meta, research_context),
        "had_substantive_graph": substantive_graph(gmeta),
    }
    report = (final_report or "").strip()
    if not report:
        meta["skipped"] = True
        meta["summary"] = "보고서 본문 없음"
        return final_report or "", meta

    tr_json = json.dumps(sap_data_raw or [], ensure_ascii=False)[:9000]
    rc = (research_context or "").strip()
    rc_judge = rc[:12000] if rc else "(내부 지식베이스 검색 결과 없음)"
    gc = (graph_context or "").strip()
    gc_judge = gc[:8000] if gc else "(구조화 종속성 그래프 없음)"
    hr, hg = meta["had_substantive_rag"], meta["had_substantive_graph"]
    if hr and hg:
        rag_hint = (
            "**[내부 지식베이스]**, **[구조화 종속성 그래프(GraphRAG)]**, **[TR 데이터]**에 맞지 않는 "
            "구체적 사실은 근거 없음입니다. 일반 배포 권고는 근거 없음이 아닙니다."
        )
    elif hg and not hr:
        rag_hint = (
            "**[구조화 종속성 그래프]** 및 **[TR 데이터]**를 근거로 삼으세요. "
            "그래프에 있으나 TR에 없는 오브젝트를 보고서가 ‘이번 TR 변경’으로 단정하면 지적하세요."
        )
    elif hr and not hg:
        rag_hint = (
            "**[내부 지식베이스]** 및 **[TR 데이터]**에 명시되지 않은 구체적 사실은 근거 없음으로 간주합니다. "
            "일반적인 배포 권고(테스트·모니터링 등)는 근거 없음이 아닙니다."
        )
    else:
        rag_hint = (
            "내부 벡터 RAG·그래프 근거가 비어 있습니다. "
            "**[TR 데이터]**와 회의에 없는 구체적 사실(가상의 티켓·프로그램명 등)을 지적하세요."
        )

    judge_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "당신은 SAP 배포 심의 보고서의 **근거 검증자**입니다.\n"
                + rag_hint
                + "\n보고서 전체를 읽고 `is_grounded`, `issues`, `severity`를 채우세요.",
            ),
            (
                "human",
                "[사용자 요청]\n{user_input}\n\n"
                "[TR 데이터 JSON 일부]\n{tr_json}\n\n"
                "[내부 지식베이스 / Researcher 컨텍스트]\n{research}\n\n"
                "[구조화 종속성 그래프 (GraphRAG)]\n{graph}\n\n"
                "[최종 보고서]\n{report}\n",
            ),
        ]
    )

    try:
        structured = llm_fast.with_structured_output(_GroundingJudge)
        chain = judge_prompt | structured
        j = chain.invoke(
            {
                "user_input": (user_input or "")[:2000],
                "tr_json": tr_json,
                "research": rc_judge,
                "graph": gc_judge,
                "report": report[:14000],
            }
        )
        meta["judge"] = j.model_dump()
    except Exception as e:
        _log.warning("deploy_self_rag judge failed: %s", e)
        meta["error"] = "Judge 실패"
        meta["summary"] = "Self-RAG 심사 생략(오류)"
        return final_report, meta

    meta["summary"] = (
        f"Self-RAG: grounded={j.is_grounded}, severity={j.severity}, issues={len(j.issues)}"
    )

    if j.is_grounded:
        return final_report, meta

    issues_lines = [x for x in (j.issues or []) if str(x).strip()][:8]
    if not issues_lines:
        issues_lines = [
            "보고서에 TR·내부 지식베이스에 없는 구체적 사실이 있을 수 있음. 확인 가능한 내용만 남기세요."
        ]
    issues_text = "\n".join(f"- {x}" for x in issues_lines)
    revise_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "당신은 수석 아키텍트입니다. 아래 **원본 보고서**를 유지하되, 심사에서 지적된 **근거 없는 주장만** "
                "삭제·완화하거나 '담당자 확인 필요'로 바꿉니다. 구조(마크다운 제목·번호)는 최대한 유지합니다. "
                "**TR 데이터**, **[내부 지식베이스]**, **[구조화 그래프]**에 있는 사실은 보존합니다. 새로운 사실을 지어내지 마세요.",
            ),
            (
                "human",
                "[지적 사항]\n{issues}\n\n"
                "[TR 데이터]\n{tr_json}\n\n"
                "[내부 지식베이스]\n{research}\n\n"
                "[구조화 종속성 그래프]\n{graph}\n\n"
                "[원본 보고서]\n{report}\n\n"
                "수정된 **전체 보고서**만 출력하세요.",
            ),
        ]
    )
    try:
        rev_chain = revise_prompt | llm_fast
        res = rev_chain.invoke(
            {
                "issues": issues_text,
                "tr_json": tr_json[:8000],
                "research": rc_judge[:10000],
                "graph": gc_judge[:8000],
                "report": report[:16000],
            }
        )
        revised = (res.content if hasattr(res, "content") else str(res)).strip()
        if revised and len(revised) > 100:
            meta["revised"] = True
            meta["summary"] += " → 1회 보정 적용"
            return revised, meta
    except Exception as e:
        _log.warning("deploy_self_rag revise failed: %s", e)
        meta["revise_error"] = str(e)

    return final_report, meta
