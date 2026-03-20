"""코드 리뷰·배포 리포트 결과를 DB에 저장하는 헬퍼."""
from __future__ import annotations

import json
from typing import Any

from api.models import CodeReviewRecord, DeployReportRecord


def _json_safe_metadata(d: dict[str, Any]) -> dict[str, Any]:
    """LangGraph state에 비JSON 타입이 섞일 수 있어 직렬화 가능한 값만 남김."""
    out: dict[str, Any] = {}
    for k, v in d.items():
        try:
            json.dumps(v)
            out[k] = v
        except (TypeError, ValueError):
            out[k] = str(v)[:8000]
    return out


def should_persist(request_data: dict, default: bool = True) -> bool:
    """`persist: false`면 저장 생략."""
    v = request_data.get("persist", default)
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() not in ("0", "false", "no", "off")
    return bool(v)


def save_code_review_record(
    *,
    request_id: str,
    user_id: str,
    obj_name: str,
    abap_code: str,
    requirement_spec: str,
    ai_result: str,
    streamed: bool,
) -> CodeReviewRecord | None:
    if not (ai_result or "").strip():
        return None
    return CodeReviewRecord.objects.create(
        request_id=request_id or "-",
        user_id=(user_id or "")[:64],
        obj_name=(obj_name or "")[:255],
        abap_code=abap_code or "",
        requirement_spec=requirement_spec or "",
        ai_result=ai_result,
        streamed=streamed,
    )


def _deploy_extra_from_state(state: dict[str, Any]) -> dict[str, Any]:
    if not state:
        return {}
    out: dict[str, Any] = {}
    for k in (
        "rule_score",
        "deploy_risk_grade",
        "deploy_risk_reason",
        "deploy_risk_actions",
        "rule_reasons",
    ):
        if k in state:
            out[k] = state[k]
    hist = state.get("discussion_history") or ""
    if hist:
        out["discussion_history_preview"] = (hist[:2000] + "…") if len(hist) > 2000 else hist
    return out


def save_deploy_report_record(
    *,
    request_id: str,
    user_id: str,
    user_input: str,
    selected_trs: list[Any],
    final_report: str,
    graph_state: dict[str, Any] | None,
) -> DeployReportRecord | None:
    text = (final_report or "").strip()
    if not text:
        return None
    trs = selected_trs if isinstance(selected_trs, list) else []
    extra = _json_safe_metadata(_deploy_extra_from_state(graph_state or {}))
    return DeployReportRecord.objects.create(
        request_id=request_id or "-",
        user_id=(user_id or "")[:64],
        user_input=user_input or "",
        selected_trs=trs,
        final_report=text,
        extra=extra,
    )
