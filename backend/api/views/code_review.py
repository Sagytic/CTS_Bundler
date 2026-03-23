"""AI code review: ABAP source vs requirement spec, Clean ABAP, refactor suggestion."""
from __future__ import annotations

import json
import logging
import time
from collections.abc import Iterator
from typing import Any

from django.http import StreamingHttpResponse
from rest_framework import status
from rest_framework.renderers import BaseRenderer, JSONRenderer
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.config import (
    azure_openai_api_version,
    azure_openai_deployment,
    azure_openai_endpoint,
    azure_openai_key,
    llm_code_review_max_tokens,
    llm_code_review_temperature,
)
from api.observability import record_stream_usage, track_llm_request
from api.persist_ai_reports import save_code_review_record
from api.prompts.code_review import build_code_review_prompt_template
from langchain_openai import AzureChatOpenAI

_code_review_log = logging.getLogger("cts.ai")


def _delta_text(chunk: Any) -> str:
    """Extract incremental text from LangChain stream chunk (AIMessageChunk 등)."""
    if chunk is None:
        return ""
    if isinstance(chunk, str):
        return chunk
    content = getattr(chunk, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict) and part.get("type") == "text":
                parts.append(str(part.get("text", "")))
        return "".join(parts)
    return ""


def _build_chain_and_inputs(
    obj_name: str,
    abap_code_snippet: str,
    requirement_spec: str,
    *,
    streaming: bool,
) -> tuple[Any, dict[str, Any]]:
    llm = AzureChatOpenAI(
        azure_deployment=azure_openai_deployment(),
        api_version=azure_openai_api_version(),
        azure_endpoint=azure_openai_endpoint(),
        api_key=azure_openai_key(),
        temperature=llm_code_review_temperature(),
        max_tokens=llm_code_review_max_tokens(),
        streaming=streaming,
    )

    has_req = bool(requirement_spec)
    prompt_template = build_code_review_prompt_template(has_req)
    chain = prompt_template | llm
    inputs: dict[str, Any] = {
        "obj_name": obj_name,
        "abap_code": abap_code_snippet,
    }
    if has_req:
        inputs["requirement_spec"] = requirement_spec
    return chain, inputs


class _PlainTextRenderer(BaseRenderer):
    """Accept: text/plain 협상용. 스트림 응답은 StreamingHttpResponse로 직접 반환."""

    media_type = "text/plain"
    charset = "utf-8"
    format = "txt"

    def render(
        self,
        data: Any,
        accepted_media_type: str | None = None,
        renderer_context: dict[str, Any] | None = None,
    ) -> bytes:
        if data is None:
            return b""
        if isinstance(data, (dict, list)):
            return json.dumps(data, ensure_ascii=False).encode(self.charset)
        return str(data).encode(self.charset)


class AICodeReviewView(APIView):
    """POST /api/code-review/ with objName, abapCode, requirementSpec. Optional stream:true → text/plain 스트림."""

    renderer_classes = [JSONRenderer, _PlainTextRenderer]

    def post(self, request: Request) -> Response | StreamingHttpResponse:
        obj_name = request.data.get("objName", "")
        abap_code_snippet = request.data.get("abapCode", "")
        requirement_spec = (
            request.data.get("requirementSpec")
            or request.data.get("requirement_spec")
            or ""
        ).strip()
        if requirement_spec and "매핑된 현업 요구사항 티켓이 DB에 없습니다" in requirement_spec:
            requirement_spec = ""

        want_stream = bool(request.data.get("stream")) or str(
            request.query_params.get("stream", "")
        ).lower() in ("1", "true", "yes")

        if not azure_openai_key() or not azure_openai_endpoint():
            return Response(
                {"aiResult": "Azure OpenAI not configured"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        if want_stream:

            def byte_stream() -> Iterator[bytes]:
                t0 = time.perf_counter()
                stream_err: Exception | None = None
                try:
                    try:
                        from langchain_community.callbacks import get_openai_callback
                    except ImportError:
                        chain, inputs = _build_chain_and_inputs(
                            obj_name,
                            abap_code_snippet,
                            requirement_spec,
                            streaming=True,
                        )
                        for chunk in chain.stream(inputs):
                            piece = _delta_text(chunk)
                            if piece:
                                yield piece.encode("utf-8")
                        return

                    with get_openai_callback() as cb:
                        try:
                            chain, inputs = _build_chain_and_inputs(
                                obj_name,
                                abap_code_snippet,
                                requirement_spec,
                                streaming=True,
                            )
                            for chunk in chain.stream(
                                inputs, config={"callbacks": [cb]}
                            ):
                                piece = _delta_text(chunk)
                                if piece:
                                    yield piece.encode("utf-8")
                        except Exception as e:
                            stream_err = e
                            _code_review_log.exception("code_review stream chunk error")
                            yield "\n\n[오류] AI 분석 중 문제가 발생했습니다. 상세 내용은 서버 로그를 확인하세요.".encode(
                                "utf-8"
                            )
                        finally:
                            record_stream_usage(
                                "code_review_stream",
                                request,
                                cb,
                                t0=t0,
                                err=stream_err,
                                deployment=azure_openai_deployment(),
                            )
                except Exception as e:
                    _code_review_log.exception("code_review stream outer error")
                    yield "\n\n[오류] AI 분석 중 문제가 발생했습니다. 상세 내용은 서버 로그를 확인하세요.".encode("utf-8")

            resp = StreamingHttpResponse(
                byte_stream(),
                content_type="text/plain; charset=utf-8",
            )
            resp["Cache-Control"] = "no-cache"
            resp["X-Accel-Buffering"] = "no"
            return resp

        try:
            chain, inputs = _build_chain_and_inputs(
                obj_name,
                abap_code_snippet,
                requirement_spec,
                streaming=False,
            )
            with track_llm_request(
                "code_review",
                request=request,
                stream=False,
                deployment=azure_openai_deployment(),
            ):
                res = chain.invoke(inputs)
            ai_result = getattr(res, "content", None) or str(res)
            if isinstance(ai_result, list):
                ai_result = _delta_text(res)
        except Exception as e:
            _code_review_log.exception("code_review error")
            ai_result = "AI 분석 중 오류가 발생했습니다. 상세 내용은 서버 로그를 확인하세요."

        if persist:
            try:
                save_code_review_record(
                    request_id=str(req_id),
                    user_id=review_user_id,
                    obj_name=str(obj_name or ""),
                    abap_code=str(abap_code_snippet or ""),
                    requirement_spec=requirement_spec,
                    ai_result=str(ai_result or ""),
                    streamed=False,
                )
            except Exception:
                _code_review_log.exception("code_review DB persist failed (json)")

        return Response(
            {"aiResult": ai_result},
            status=status.HTTP_200_OK,
        )
