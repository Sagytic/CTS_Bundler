"""
ReAct 에이전트: LLM이 도구를 반복 호출(Reason → Act → Reason → …)하며 답변 생성.
LangGraph create_react_agent가 내부에서 도구 호출 루프를 수행하고, 응답에 steps를 넣어 ReAct 동작을 노출.
"""
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
    azure_openai_endpoint,
    azure_openai_fast_deployment,
    azure_openai_key,
    llm_agent_recursion_limit,
    llm_agent_temperature,
    mcp_adt_configured,
    mcp_docs_configured,
    rag_default_k,
)
from api.observability import record_stream_usage, track_llm_request
from api.prompts.agent import build_agent_system_prompt
from langchain_openai import AzureChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

from api.agent_reply_cleanup import clean_agent_reply_text
from api.sap_client import fetch_recent_transports_via_http, filter_main_transports
from api.models import DependencySnapshot, TicketMapping

_logger = logging.getLogger("cts.ai")


def _query_smells_like_public_sap_docs(q: str) -> bool:
    """Help/문서/가이드 등 공식 문서 성격 질문(내부 RAG로 대체하면 안 됨)."""
    q_raw = q or ""
    ql = q_raw.casefold()
    for needle in (
        "help",
        "documentation",
        "ddic",
        "reference",
        "guide",
        "official",
        "keyword",
        "clean abap",
        "문서",
        "가이드",
        "공식",
        "레퍼런스",
        "도움말",
        "검색해서",
        "검색 해서",
    ):
        if needle in ql:
            return True
    for needle in ("Help", "문서", "MCP"):
        if needle in q_raw:
            return True
    return False


def _delta_text(chunk: Any) -> str:
    """스트림 청크(AIMessageChunk 등)에서 증분 텍스트 추출."""
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


def _messages_from_values_state(val: Any) -> list:
    if val is None:
        return []
    if isinstance(val, dict):
        return list(val.get("messages") or [])
    msgs = getattr(val, "messages", None)
    return list(msgs) if msgs else []


def _trailer_meta_bytes(
    latest_state: Any, include_steps: bool, stream_err: BaseException | None
) -> bytes:
    messages = _messages_from_values_state(latest_state)
    steps = _extract_react_steps(messages) if include_steps else []
    meta: dict[str, Any] = {
        "steps": steps,
        "react_used_tools": len([s for s in steps if s.get("type") == "tool_call"]),
    }
    if stream_err is not None:
        meta["error"] = str(stream_err)
    return ("\x1e" + json.dumps(meta, ensure_ascii=False, default=str)).encode("utf-8")


def _extract_react_steps(messages):
    """메시지 히스토리에서 도구 호출(Act)과 결과를 추출해 ReAct 단계 목록으로 반환."""
    steps = []
    for m in messages:
        if isinstance(m, AIMessage) and getattr(m, "tool_calls", None):
            for tc in m.tool_calls:
                name = tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", "")
                args = tc.get("args") if isinstance(tc, dict) else getattr(tc, "args", {})
                steps.append({"type": "tool_call", "tool": name, "args": args})
        if isinstance(m, ToolMessage):
            content = getattr(m, "content", str(m))[:2000]  # 길이 제한
            steps.append({"type": "tool_result", "content_preview": content})
    return steps


def _make_tools() -> tuple[list[Any], dict[str, int]]:
    @tool
    def list_transports(user_id: str) -> str:
        """사용자별 최근 메인 TR 목록 조회(Workbench K / Customizing W만, Analyzer와 동일). user_id는 SAP 사번(예: 11355)."""
        r = fetch_recent_transports_via_http(user_id=user_id)
        if r["status"] != "success":
            return f"조회 실패: {r.get('message', '')}\n\n"
        raw = r.get("data", [])
        data = filter_main_transports(raw if isinstance(raw, list) else [])[:30]
        lines = "\n".join(
            [
                f"- {t.get('TRKORR', t.get('trkorr'))}: {t.get('AS4TEXT', t.get('as4text', ''))}"
                for t in data
            ]
        ) or "TR 없음"
        # 끝에 빈 줄: 다음 도구 결과와 붙어 ZAI티켓: 같은 결합 방지
        return f"{lines}\n\n"

    @tool
    def get_dependency_edges(target_obj: str) -> str:
        """SAP 오브젝트의 호출 관계(종속성)만 조회. 'A가 B를 호출한다' 같은 관계만 반환하며, 소스 코드·테이블 필드 구조는 반환하지 않음. 클래스/테이블 소스나 구조가 필요하면 GetClass·GetTable 사용. target_obj는 대문자(예: ZMMR0030)."""
        t = (target_obj or "").strip().upper()
        if not t:
            return "target_obj 입력 필요"
        fwd = list(DependencySnapshot.objects.filter(source_obj=t).values_list("target_obj", flat=True)[:50])
        bwd = list(DependencySnapshot.objects.filter(target_obj=t).values_list("source_obj", flat=True)[:50])
        return f"{t} → 호출: {', '.join(fwd) or '없음'}\n{t} ← 호출당함: {', '.join(bwd) or '없음'}"

    @tool
    def get_ticket_mapping(trkorr: str) -> str:
        """TR에 매핑된 티켓·요구사항 조회. trkorr는 list_transports 결과의 TRKORR만 사용(가상 번호 금지)."""
        key = (trkorr or "").strip()
        if not key:
            return "trkorr 입력 필요"
        try:
            o = TicketMapping.objects.get(target_key=key)
            return f"티켓: {o.ticket_id}\n요구사항: {o.description}\n\n"
        except TicketMapping.DoesNotExist:
            return f"[{key}] 매핑 없음\n\n"

    @tool
    def search_rag(query: str) -> str:
        """CTS Bundler **내부** RAG 인덱스만 검색(인제스트된 TR/종속성/티켓 메모 등).

        SAP Help/공식 문서/가이드 질문에는 사용 금지 — **SAP Docs MCP** 우선.
        Docs MCP URL이 비어 있으면 서버가 이 도구로 **검색 자체를 막을 수** 있음(종속성 노이즈 방지)."""
        from api.rag import services

        q = (query or "").strip()
        if not q:
            return "query 입력 필요\n\n"
        if _query_smells_like_public_sap_docs(q):
            return (
                "[내부] 문서/Help/가이드 성격 — **내부 RAG retrieve 미실행**. search_rag 호출은 잘못된 선택입니다. "
                "**SAP Docs MCP 도구**로만 답하세요. MCP 도구가 없으면 URL은 있어도 tools/list 실패(로그 `agent.react tools`)일 수 있음 — "
                "연결·Streamable HTTP·경로 확인을 사용자에게 한 줄 안내 후, Clean ABAP·가독성 등 일반 요약만 하세요.\n\n"
            )
        try:
            results = services.retrieve(q, k=rag_default_k())
            body = "\n".join([d.page_content for d, _ in results]) or "관련 문서 없음"
            return f"{body}\n\n"
        except Exception as e:
            return f"검색 오류: {e}\n\n"

    # 로컬 도구 → MCP(Docs/ADT) → 마지막에 search_rag
    tools: list = [list_transports, get_dependency_edges, get_ticket_mapping]
    n_docs = 0
    n_adt = 0

    try:
        from api.mcp_client import get_external_sap_docs_tools

        docs_list = get_external_sap_docs_tools()
        n_docs = len(docs_list)
        tools.extend(docs_list)
    except Exception:
        pass

    try:
        from api.mcp_client import get_external_adt_tools

        adt_list = get_external_adt_tools()
        n_adt = len(adt_list)
        tools.extend(adt_list)
    except Exception:
        pass

    tools.append(search_rag)

    du = mcp_docs_configured()
    au = mcp_adt_configured()
    if du and n_docs == 0:
        _logger.warning(
            "agent.react: EXTERNAL_SAP_MCP_DOCS_* URL is set but 0 Docs MCP tools loaded "
            "(check Streamable HTTP reachability from Django host)"
        )
    if au and n_adt == 0:
        _logger.warning(
            "agent.react: EXTERNAL_SAP_MCP_ADT_URL is set but 0 ADT MCP tools loaded"
        )

    _logger.info(
        "agent.react tools: docs_url=%s docs_tools=%s adt_url=%s adt_tools=%s total=%s",
        du,
        n_docs,
        au,
        n_adt,
        len(tools),
    )

    return tools, {"docs_tools": n_docs, "adt_tools": n_adt}


class _PlainTextRenderer(BaseRenderer):
    """Accept: text/plain 협상용. 스트림은 StreamingHttpResponse로 직접 반환."""

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


class AgentChatView(APIView):
    """POST /api/agent/ with {"message": "..."}. ReAct agent with tools."""

    renderer_classes = [JSONRenderer, _PlainTextRenderer]

    def post(self, request: Request) -> Response | StreamingHttpResponse:
        user_input = (
            request.data.get("message") or request.data.get("input") or ""
        ).strip()
        if not user_input:
            return Response(
                {"error": "message required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        sap_user_id = (
            request.data.get("user_id")
            or request.data.get("sap_user_id")
            or ""
        )
        sap_user_id = str(sap_user_id).strip()

        if not azure_openai_key() or not azure_openai_endpoint():
            return Response(
                {"error": "Azure OpenAI not configured"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        want_stream = bool(request.data.get("stream")) or str(
            request.query_params.get("stream", "")
        ).lower() in ("1", "true", "yes")

        include_steps = request.data.get("include_steps", True)

        human_content = user_input
        if sap_user_id:
            human_content = (
                f"[SAP 사용자 ID: {sap_user_id} — TR 관련 질문 시 list_transports에 이 user_id를 사용]\n"
                + user_input
            )
        react_cfg: dict[str, Any] = {"recursion_limit": llm_agent_recursion_limit()}
        agent_inputs: dict[str, Any] = {
            "messages": [HumanMessage(content=human_content)]
        }

        try:
            from langgraph.prebuilt import create_react_agent

            llm = AzureChatOpenAI(
                azure_deployment=azure_openai_fast_deployment(),
                api_version=azure_openai_api_version(),
                azure_endpoint=azure_openai_endpoint(),
                api_key=azure_openai_key(),
                temperature=llm_agent_temperature(),
                streaming=bool(want_stream),
            )
            tools, mcp_counts = _make_tools()
            du = mcp_docs_configured()
            au = mcp_adt_configured()
            nd = mcp_counts["docs_tools"]
            na = mcp_counts["adt_tools"]
            system = build_agent_system_prompt(
                sap_user_id,
                docs_mcp_effective=bool(du and nd > 0),
                docs_url_set_no_tools=bool(du and nd == 0),
                adt_mcp_effective=bool(au and na > 0),
                adt_url_set_no_tools=bool(au and na == 0),
            )
            graph = create_react_agent(llm, tools, prompt=system)
        except Exception as e:
            return Response(
                {
                    "reply": f"에이전트 초기화 오류: {str(e)}",
                    "steps": [],
                    "react_used_tools": 0,
                    "error": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if want_stream:

            def byte_stream() -> Iterator[bytes]:
                t0 = time.perf_counter()
                stream_err: BaseException | None = None
                latest_holder: list[Any] = [None]

                def run_chunks(loop_cfg: dict[str, Any]) -> Iterator[bytes]:
                    for chunk in graph.stream(
                        agent_inputs,
                        config=loop_cfg,
                        stream_mode=["messages", "values"],
                    ):
                        if isinstance(chunk, tuple) and len(chunk) == 2:
                            mode, payload = chunk
                            if mode == "values":
                                latest_holder[0] = payload
                            elif mode == "messages":
                                if (
                                    isinstance(payload, tuple)
                                    and len(payload) >= 1
                                ):
                                    piece = _delta_text(payload[0])
                                    if piece:
                                        yield piece.encode("utf-8")

                try:
                    from langchain_community.callbacks import get_openai_callback
                except ImportError:
                    try:
                        yield from run_chunks(react_cfg)
                    except BaseException as e:
                        stream_err = e
                        yield f"\n\n[오류] 에이전트 실행 오류: {e}".encode("utf-8")
                    finally:
                        yield _trailer_meta_bytes(
                            latest_holder[0], include_steps, stream_err
                        )
                    return

                with get_openai_callback() as cb:
                    try:
                        yield from run_chunks(
                            {**react_cfg, "callbacks": [cb]}
                        )
                    except BaseException as e:
                        stream_err = e
                        yield f"\n\n[오류] 에이전트 실행 오류: {e}".encode(
                            "utf-8"
                        )
                    finally:
                        yield _trailer_meta_bytes(
                            latest_holder[0], include_steps, stream_err
                        )
                        record_stream_usage(
                            "agent_react_stream",
                            request,
                            cb,
                            t0=t0,
                            err=stream_err,
                            deployment=azure_openai_fast_deployment(),
                            recursion_limit=react_cfg["recursion_limit"],
                        )

            resp = StreamingHttpResponse(
                byte_stream(),
                content_type="text/plain; charset=utf-8",
            )
            resp["Cache-Control"] = "no-cache"
            resp["X-Accel-Buffering"] = "no"
            return resp

        try:
            with track_llm_request(
                "agent_react",
                request=request,
                deployment=azure_openai_fast_deployment(),
                recursion_limit=react_cfg["recursion_limit"],
            ):
                result = graph.invoke(agent_inputs, config=react_cfg)
            messages = result.get("messages", [])
            reply = "응답을 생성하지 못했습니다."
            fallback_reply = reply
            for m in reversed(messages):
                if not isinstance(m, AIMessage):
                    continue
                content = getattr(m, "content", None)
                if not content:
                    continue
                text = content if isinstance(content, str) else str(content)
                if not getattr(m, "tool_calls", None):
                    reply = text
                    break
                fallback_reply = text
            if (
                reply == "응답을 생성하지 못했습니다."
                and fallback_reply != "응답을 생성하지 못했습니다."
            ):
                reply = fallback_reply

            reply = clean_agent_reply_text(reply)

            steps = _extract_react_steps(messages) if include_steps else []
            return Response(
                {
                    "reply": reply,
                    "steps": steps,
                    "react_used_tools": len(
                        [s for s in steps if s.get("type") == "tool_call"]
                    ),
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {
                    "reply": f"에이전트 실행 오류: {str(e)}",
                    "steps": [],
                    "react_used_tools": 0,
                    "error": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
