"""
LLM token usage aggregates for the Token Dashboard.

- **SQLite(DB)에 이벤트 단위로 저장** — 서버 재시작 후에도 누적이 유지됩니다.
- 다중 워커(gunicorn)에서도 동일 DB를 보면 합산됩니다. 정확한 청구는 Azure Portal 기준입니다.
"""
from __future__ import annotations

from datetime import timezone as dt_timezone
from typing import Any
from zoneinfo import ZoneInfo

from django.db.models import Count, Sum
from django.utils import timezone

KST = ZoneInfo("Asia/Seoul")

_recent_limit = 200


def _bootstrap_recent_max() -> None:
    try:
        from api.config import llm_usage_recent_max

        configure_recent_max(llm_usage_recent_max())
    except Exception:
        pass


_bootstrap_recent_max()


def configure_recent_max(n: int) -> None:
    global _recent_limit
    _recent_limit = max(10, min(5000, n))


def tokens_from_openai_callback(cb: Any) -> tuple[int, int, int]:
    """LangChain OpenAICallbackHandler-compatible object."""
    pt = int(getattr(cb, "prompt_tokens", 0) or 0)
    ct = int(getattr(cb, "completion_tokens", 0) or 0)
    tt = int(getattr(cb, "total_tokens", 0) or 0)
    if tt <= 0:
        tt = pt + ct
    return pt, ct, tt


def _fmt_kst(dt: Any) -> str:
    if dt is None:
        return ""
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, dt_timezone.utc)
    return dt.astimezone(KST).strftime("%Y-%m-%d %H:%M:%S")


def _row_to_dict(r: Any) -> dict[str, Any]:
    ca = r.created_at
    return {
        "ts": ca.timestamp(),
        "ts_iso": ca.astimezone(dt_timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ts_kst": _fmt_kst(ca),
        "operation": r.operation,
        "request_id": r.request_id,
        "prompt_tokens": r.prompt_tokens,
        "completion_tokens": r.completion_tokens,
        "total_tokens": r.total_tokens,
        "duration_ms": round(float(r.duration_ms), 2),
        "ok": r.ok,
        "extra": r.extra or {},
    }


def record_llm_usage(
    operation: str,
    request_id: str,
    *,
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
    duration_ms: float,
    ok: bool,
    extra: dict[str, Any] | None = None,
) -> None:
    from api.config import llm_usage_tracking_enabled
    from api.models import LlmUsageRecord

    if not llm_usage_tracking_enabled():
        return

    LlmUsageRecord.objects.create(
        operation=(operation or "")[:128],
        request_id=(request_id or "-")[:128],
        prompt_tokens=max(0, int(prompt_tokens)),
        completion_tokens=max(0, int(completion_tokens)),
        total_tokens=max(0, int(total_tokens)),
        duration_ms=float(duration_ms),
        ok=bool(ok),
        extra=dict(extra or {}),
    )


def snapshot() -> dict[str, Any]:
    from api.models import LlmUsageRecord

    qs = LlmUsageRecord.objects.all()
    agg = qs.aggregate(
        total_calls=Count("id"),
        total_prompt=Sum("prompt_tokens"),
        total_completion=Sum("completion_tokens"),
    )
    total_calls = int(agg["total_calls"] or 0)
    total_prompt = int(agg["total_prompt"] or 0)
    total_completion = int(agg["total_completion"] or 0)

    by_op: dict[str, dict[str, int]] = {}
    for row in (
        qs.values("operation")
        .annotate(
            calls=Count("id"),
            prompt_tokens=Sum("prompt_tokens"),
            completion_tokens=Sum("completion_tokens"),
            total_tokens=Sum("total_tokens"),
        )
        .order_by("operation")
    ):
        op = row["operation"]
        by_op[op] = {
            "calls": int(row["calls"] or 0),
            "prompt_tokens": int(row["prompt_tokens"] or 0),
            "completion_tokens": int(row["completion_tokens"] or 0),
            "total_tokens": int(row["total_tokens"] or 0),
        }

    first = qs.order_by("created_at").first()
    if first:
        server_started_at = first.created_at.timestamp()
        server_started_kst = _fmt_kst(first.created_at)
    else:
        server_started_at = None
        server_started_kst = None

    recent_qs = qs.order_by("-created_at")[:_recent_limit]
    recent = [_row_to_dict(r) for r in recent_qs]

    return {
        "server_started_at": server_started_at,
        "server_started_at_iso": (
            f"{server_started_kst} (UTC+9)" if server_started_kst else None
        ),
        "server_started_at_kst": server_started_kst,
        "summary": {
            "total_calls": total_calls,
            "total_prompt_tokens": total_prompt,
            "total_completion_tokens": total_completion,
            "total_tokens": total_prompt + total_completion,
        },
        "by_operation": by_op,
        "recent": recent,
    }


def reset_all() -> None:
    from api.models import LlmUsageRecord

    LlmUsageRecord.objects.all().delete()
