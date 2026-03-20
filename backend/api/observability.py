"""
LLM / AI call observability helpers.

Use with RequestContextMiddleware so logs include request_id.

LangSmith (optional): set in the environment (no extra Python dependency required):
  LANGCHAIN_TRACING_V2=true
  LANGCHAIN_API_KEY=<key>
  LANGCHAIN_PROJECT=cts-bundler

LangChain/LangGraph will pick these up when invoking chains.

토큰 집계: `track_llm_request` + `langchain-community` 의 `get_openai_callback`.
"""
from __future__ import annotations

import logging
import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

logger = logging.getLogger("cts.ai")


def request_id_from(request: Any) -> str:
    """Safe accessor for middleware-set correlation id."""
    return getattr(request, "request_id", None) or "-"


@contextmanager
def llm_span(
    operation: str,
    *,
    request: Any | None = None,
    request_id: str | None = None,
    **extra: Any,
) -> Iterator[None]:
    """
    Duration-only log (토큰 없음). 레거시·폴백용.
    """
    rid = request_id if request_id is not None else (
        request_id_from(request) if request is not None else "-"
    )
    t0 = time.perf_counter()
    err: BaseException | None = None
    try:
        yield
    except BaseException as e:
        err = e
        raise
    finally:
        ms = (time.perf_counter() - t0) * 1000
        ok = err is None
        extra_bits = " ".join(f"{k}={v!r}" for k, v in extra.items())
        logger.info(
            "llm.%s request_id=%s duration_ms=%.2f ok=%s%s",
            operation,
            rid,
            ms,
            ok,
            f" {extra_bits}" if extra_bits else "",
        )


def _log_llm_tokens(
    operation: str,
    rid: str,
    t0: float,
    err: BaseException | None,
    *,
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
    **extra: Any,
) -> None:
    ms = (time.perf_counter() - t0) * 1000
    ok = err is None
    extra_bits = " ".join(f"{k}={v!r}" for k, v in extra.items())
    logger.info(
        "llm.%s request_id=%s duration_ms=%.2f ok=%s prompt_tokens=%s completion_tokens=%s total_tokens=%s%s",
        operation,
        rid,
        ms,
        ok,
        prompt_tokens,
        completion_tokens,
        total_tokens,
        f" {extra_bits}" if extra_bits else "",
    )


@contextmanager
def track_llm_request(
    operation: str,
    *,
    request: Any | None = None,
    request_id: str | None = None,
    **extra: Any,
) -> Iterator[None]:
    """
    LangChain OpenAI 호출을 감싸 토큰·지속시간을 usage_metrics + 로그에 기록.

    반드시 이 컨텍스트 **안에서** chain.invoke / graph.invoke 를 실행하세요.
    """
    from api.config import llm_usage_tracking_enabled

    rid = (
        request_id
        if request_id is not None
        else (request_id_from(request) if request is not None else "-")
    )
    t0 = time.perf_counter()
    err: BaseException | None = None

    if not llm_usage_tracking_enabled():
        try:
            yield
        except BaseException as e:
            err = e
            raise
        finally:
            _log_llm_tokens(
                operation,
                rid,
                t0,
                err,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                **extra,
            )
        return

    try:
        from langchain_community.callbacks import get_openai_callback
    except ImportError:
        logger.warning(
            "langchain-community missing; install for token tracking. pip install langchain-community"
        )
        try:
            yield
        except BaseException as e:
            err = e
            raise
        finally:
            _log_llm_tokens(
                operation,
                rid,
                t0,
                err,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                **extra,
            )
        return

    from api.usage_metrics import record_llm_usage, tokens_from_openai_callback

    with get_openai_callback() as cb:
        try:
            yield
        except BaseException as e:
            err = e
            raise
        finally:
            pt, ct, tt = tokens_from_openai_callback(cb)
            ms = (time.perf_counter() - t0) * 1000
            ok = err is None
            record_llm_usage(
                operation,
                rid,
                prompt_tokens=pt,
                completion_tokens=ct,
                total_tokens=tt,
                duration_ms=ms,
                ok=ok,
                extra={k: str(v)[:200] for k, v in extra.items()},
            )
            _log_llm_tokens(
                operation,
                rid,
                t0,
                err,
                prompt_tokens=pt,
                completion_tokens=ct,
                total_tokens=tt,
                **extra,
            )


def record_stream_usage(
    operation: str,
    request: Any | None,
    cb: Any,
    *,
    t0: float,
    err: BaseException | None,
    **extra: Any,
) -> None:
    """스트리밍 종료 후 OpenAICallbackHandler 로 집계."""
    from api.config import llm_usage_tracking_enabled

    if not llm_usage_tracking_enabled():
        return
    rid = request_id_from(request) if request is not None else "-"
    from api.usage_metrics import record_llm_usage, tokens_from_openai_callback

    pt, ct, tt = tokens_from_openai_callback(cb)
    ms = (time.perf_counter() - t0) * 1000
    ok = err is None
    record_llm_usage(
        operation,
        rid,
        prompt_tokens=pt,
        completion_tokens=ct,
        total_tokens=tt,
        duration_ms=ms,
        ok=ok,
        extra={k: str(v)[:200] for k, v in extra.items()},
    )
    _log_llm_tokens(
        operation,
        rid,
        t0,
        err,
        prompt_tokens=pt,
        completion_tokens=ct,
        total_tokens=tt,
        **extra,
    )
