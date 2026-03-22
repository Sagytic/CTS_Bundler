"""
배포 심의 RAG 파이프라인 4단계: 플래그 해석·요약 메타.

- 환경 변수 기본값 + POST body `pipeline` 로 요청별 오버라이드
- 그래프 실행 후 `build_deploy_pipeline_summary` 로 관측용 요약(JSON 안전)
"""
from __future__ import annotations

from typing import Any

_PIPELINE_KEYS = (
    ("research", "research_rag"),
    ("graph", "graph_rag"),
    ("self_rag", "self_rag"),
    ("crag_judge", "crag_judge"),
)


def resolve_deploy_pipeline_flags(request_data: dict) -> dict[str, bool]:
    """
    최종 플래그 dict (모든 키 bool).

    Body 예시::
        "pipeline": { "research": true, "graph": false, "self_rag": true, "crag_judge": false }
    """
    from api.config import (
        deploy_crag_judge_enabled,
        deploy_graph_rag_enabled,
        deploy_research_rag_enabled,
        deploy_self_rag_enabled,
    )

    base: dict[str, bool] = {
        "research_rag": deploy_research_rag_enabled(),
        "graph_rag": deploy_graph_rag_enabled(),
        "self_rag": deploy_self_rag_enabled(),
        "crag_judge": deploy_crag_judge_enabled(),
    }
    p = request_data.get("pipeline")
    if not isinstance(p, dict):
        return base
    for api_key, flag_key in _PIPELINE_KEYS:
        if api_key in p:
            base[flag_key] = bool(p[api_key])
    # 벡터 RAG 끄면 CRAG 판정만 켜는 건 의미 없음 → 정리
    if not base["research_rag"]:
        base["crag_judge"] = False
    return base


def build_deploy_pipeline_summary(state: dict[str, Any] | None) -> dict[str, Any]:
    """DB extra·NDJSON(선택)용 컴팩트 요약."""
    if not state:
        return {}
    flags = state.get("pipeline_flags") or {}
    rmeta = state.get("research_meta") or {}
    gmeta = state.get("graph_meta") or {}
    smeta = state.get("self_rag_meta") or {}
    judge = smeta.get("judge") if isinstance(smeta.get("judge"), dict) else {}

    return {
        "flags": dict(flags),
        "timings_ms": dict(state.get("pipeline_timings_ms") or {}),
        "research": {
            "rounds": len(rmeta.get("rounds") or []),
            "empty": bool(rmeta.get("empty")),
            "skipped": rmeta.get("skipped"),
        },
        "graph": {
            "edges": int(gmeta.get("edge_count") or 0),
            "seeds": int(gmeta.get("seed_count") or 0),
            "skipped": bool(gmeta.get("skipped")),
        },
        "self_rag": {
            "skipped": bool(smeta.get("skipped")),
            "revised": bool(smeta.get("revised")),
            "is_grounded": judge.get("is_grounded"),
            "severity": judge.get("severity"),
        },
    }
