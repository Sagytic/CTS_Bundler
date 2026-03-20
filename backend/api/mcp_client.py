"""
외부 MCP 서버(SAP Docs, ABAP ADT 등)에 연결해 도구 목록을 가져오고,
ReAct 에이전트에서 호출할 수 있는 LangChain 도구로 래핑합니다.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import httpx
import mcp.types as types
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamable_http_client
from mcp.shared._httpx_utils import MCP_DEFAULT_SSE_READ_TIMEOUT, MCP_DEFAULT_TIMEOUT

from api import config as app_config

_mcp_log = logging.getLogger("cts.ai")
_mcp_ssl_verify_warned = False


# 툴 목록/세션 캐시 (프로세스당 1회 조회, 이후 호출 시 재사용)
_remote_tools_cache: dict[str, list[dict[str, Any]]] = {}


def _exception_leaves(exc: BaseException, *, max_leaves: int = 8) -> list[str]:
    """TaskGroup/ExceptionGroup 안의 실제 원인을 로그용 문자열로 펼침."""
    out: list[str] = []

    def walk(e: BaseException) -> None:
        if len(out) >= max_leaves:
            return
        if isinstance(e, BaseExceptionGroup):
            for sub in e.exceptions:
                walk(sub)
                if len(out) >= max_leaves:
                    return
        else:
            out.append(f"{type(e).__name__}: {e}")

    walk(exc)
    return out


def _log_mcp_failure(phase: str, url: str, exc: BaseException) -> None:
    leaves = _exception_leaves(exc)
    detail = " | ".join(leaves) if leaves else repr(exc)
    _mcp_log.warning("mcp %s failed url=%s detail=%s", phase, url[:160], detail[:1500])


def _create_mcp_httpx_client(
    headers: dict[str, str] | None = None,
    timeout: httpx.Timeout | None = None,
    auth: httpx.Auth | None = None,
) -> httpx.AsyncClient:
    """httpx.AsyncClient with same defaults as MCP, plus optional SSL verify off."""
    global _mcp_ssl_verify_warned
    verify = app_config.mcp_http_verify_ssl()
    if not verify and not _mcp_ssl_verify_warned:
        _mcp_ssl_verify_warned = True
        _mcp_log.warning(
            "MCP TLS verify disabled (EXTERNAL_SAP_MCP_VERIFY_SSL=false). "
            "Insecure; prefer installing your org CA or use only on trusted networks."
        )
    kwargs: dict[str, Any] = {"follow_redirects": True, "verify": verify}
    if timeout is None:
        kwargs["timeout"] = httpx.Timeout(MCP_DEFAULT_TIMEOUT, read=MCP_DEFAULT_SSE_READ_TIMEOUT)
    else:
        kwargs["timeout"] = timeout
    if headers is not None:
        kwargs["headers"] = headers
    if auth is not None:
        kwargs["auth"] = auth
    return httpx.AsyncClient(**kwargs)


async def _session_list_tool_defs(session: ClientSession) -> list[dict[str, Any]]:
    await session.initialize()
    result = await session.list_tools()
    tools: list[dict[str, Any]] = []
    for t in result.tools:
        name = getattr(t, "name", None) or (
            (t.model_dump() if hasattr(t, "model_dump") else {}).get("name")
        )
        if not name:
            continue
        desc = getattr(t, "description", None) or ""
        schema = getattr(t, "inputSchema", None) or {}
        tools.append({"name": name, "description": desc or name, "inputSchema": schema})
    return tools


async def _fetch_remote_tools_streamable(url: str) -> list[dict[str, Any]]:
    async with _create_mcp_httpx_client(timeout=httpx.Timeout(45.0, read=120.0)) as client:
        async with streamable_http_client(url, http_client=client) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                return await _session_list_tool_defs(session)


async def _fetch_remote_tools_sse(url: str) -> list[dict[str, Any]]:
    async with sse_client(
        url,
        timeout=45.0,
        sse_read_timeout=120.0,
        httpx_client_factory=_create_mcp_httpx_client,
    ) as (
        read_stream,
        write_stream,
    ):
        async with ClientSession(read_stream, write_stream) as session:
            return await _session_list_tool_defs(session)


def _content_to_text(result: types.CallToolResult) -> str:
    """CallToolResult의 content 리스트에서 텍스트만 추출해 합칩니다."""
    parts = []
    for block in result.content or []:
        if isinstance(block, types.TextContent):
            parts.append(block.text)
        elif hasattr(block, "text"):
            parts.append(block.text)
        elif isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text", ""))
    return "\n".join(parts) if parts else (result.structuredContent and json.dumps(result.structuredContent, ensure_ascii=False) or "응답 없음")


async def _fetch_remote_tools(url: str) -> list[dict[str, Any]]:
    """외부 MCP 서버에 연결해 tools/list 결과를 반환합니다. Streamable HTTP 실패 시 SSE 전송으로 재시도."""
    if not url or not url.strip():
        return []
    url = url.strip()
    try:
        tools = await _fetch_remote_tools_streamable(url)
        if tools:
            _mcp_log.info(
                "mcp.tools/list ok transport=streamable_http url=%s count=%s",
                url[:120],
                len(tools),
            )
        return tools
    except BaseException as e:
        _log_mcp_failure("tools/list streamable_http", url, e)

    try:
        tools = await _fetch_remote_tools_sse(url)
        _mcp_log.info(
            "mcp.tools/list ok transport=sse url=%s count=%s",
            url[:120],
            len(tools),
        )
        return tools
    except BaseException as e:
        _log_mcp_failure("tools/list sse", url, e)
        return []


async def _call_remote_tool_session(
    tool_name: str, arguments: dict[str, Any] | None, session: ClientSession
) -> str:
    await session.initialize()
    result = await session.call_tool(tool_name, arguments or {})
    if result.isError:
        return f"도구 실행 오류: {getattr(result, 'content', result)}"
    return _content_to_text(result)


async def _call_remote_tool(url: str, tool_name: str, arguments: dict[str, Any] | None) -> str:
    """외부 MCP 서버의 도구를 한 번 호출하고 결과 텍스트를 반환합니다."""
    if not url or not url.strip():
        return "외부 MCP URL이 설정되지 않았습니다."
    url = url.strip()
    try:
        async with _create_mcp_httpx_client(timeout=httpx.Timeout(45.0, read=120.0)) as client:
            async with streamable_http_client(url, http_client=client) as (read_stream, write_stream, _):
                async with ClientSession(read_stream, write_stream) as session:
                    return await _call_remote_tool_session(tool_name, arguments, session)
    except BaseException as e:
        _log_mcp_failure(f"call_tool streamable_http tool={tool_name}", url, e)

    try:
        async with sse_client(
            url,
            timeout=45.0,
            sse_read_timeout=120.0,
            httpx_client_factory=_create_mcp_httpx_client,
        ) as (
            read_stream,
            write_stream,
        ):
            async with ClientSession(read_stream, write_stream) as session:
                return await _call_remote_tool_session(tool_name, arguments, session)
    except BaseException as e:
        _log_mcp_failure(f"call_tool sse tool={tool_name}", url, e)
        leaves = _exception_leaves(e)
        hint = leaves[0] if leaves else str(e)
        return f"외부 MCP 호출 오류: {hint}"


def _run_async(coro):
    """Django(동기) 환경에서 async 함수를 실행합니다."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    if loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, coro)
            return future.result()
    return loop.run_until_complete(coro)


def _make_remote_tool(url: str, tool_name: str, description: str, input_schema: dict):
    """원격 MCP 도구 하나를 LangChain StructuredTool로 래핑합니다."""
    from langchain_core.tools import StructuredTool
    from pydantic import create_model

    props = (input_schema or {}).get("properties") or {}
    required = set((input_schema or {}).get("required") or [])
    fields = {}
    for key, spec in props.items():
        typ = (spec or {}).get("type", "string")
        desc = (spec or {}).get("description") or key
        if typ == "integer" or typ == "number":
            fields[key] = (int, None if key not in required else ...)
        else:
            fields[key] = (str, None if key not in required else ...)
    if not fields:
        fields["query"] = (str, ...)  # 기본 단일 인자
    ArgsSchema = create_model(f"Args_{tool_name}", **fields)

    def _invoke(**kwargs) -> str:
        return _run_async(_call_remote_tool(url, tool_name, kwargs))

    return StructuredTool.from_function(
        name=tool_name,
        description=description or tool_name,
        func=_invoke,
        args_schema=ArgsSchema,
    )


def get_external_sap_docs_tools() -> list:
    """EXTERNAL_SAP_MCP_DOCS_ABAP_URL 또는 DOCS_FULL_URL이 있으면 해당 MCP 도구 목록을 LangChain 도구로 반환합니다."""
    url = app_config.mcp_docs_url()
    if not url.strip():
        return []
    cache_key = f"docs:{url}"
    if cache_key not in _remote_tools_cache:
        _remote_tools_cache[cache_key] = _run_async(_fetch_remote_tools(url))
    tools_def = _remote_tools_cache[cache_key]
    out = []
    for t in tools_def:
        try:
            out.append(_make_remote_tool(url, t["name"], t["description"] or "", t.get("inputSchema") or {}))
        except Exception:
            continue
    return out


def get_external_adt_tools() -> list:
    """EXTERNAL_SAP_MCP_ADT_URL이 있고, ADT 도구 화이트리스트(GetClass, GetTable 등)에 해당하는 도구만 반환합니다."""
    url = app_config.mcp_adt_url()
    if not url.strip():
        return []
    whitelist = app_config.mcp_adt_tools_whitelist()
    allowed = {s.strip() for s in whitelist.split(",") if s.strip()} or {"GetClass", "GetTable"}
    cache_key = f"adt:{url}"
    if cache_key not in _remote_tools_cache:
        _remote_tools_cache[cache_key] = _run_async(_fetch_remote_tools(url))
    tools_def = _remote_tools_cache[cache_key]
    out = []
    for t in tools_def:
        name = t.get("name") or ""
        if name not in allowed:
            continue
        try:
            out.append(_make_remote_tool(url, name, t["description"] or "", t.get("inputSchema") or {}))
        except Exception:
            continue
    return out
