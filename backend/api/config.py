"""
Centralized configuration from environment variables.

All access to os.getenv for app config should go through this module
so defaults and types are consistent and testable.
"""
from __future__ import annotations

import os
from typing import Optional


def env(key: str, default: str = "") -> str:
    """Get string env var with default."""
    return (os.getenv(key) or default).strip()


def env_bool(key: str, default: bool = False) -> bool:
    """Get bool from env (true/1/yes)."""
    v = (os.getenv(key) or "").strip().lower()
    if not v:
        return default
    return v in ("true", "1", "yes")


def env_int(key: str, default: int = 0) -> int:
    """Get int from env."""
    try:
        return int(os.getenv(key) or default)
    except ValueError:
        return default


def env_float(key: str, default: float = 0.0) -> float:
    """Get float from env."""
    try:
        raw = os.getenv(key)
        if raw is None or str(raw).strip() == "":
            return default
        return float(raw)
    except ValueError:
        return default


# --- SAP HTTP (CTS API) ---


def sap_http_url() -> str:
    return env("SAP_HTTP_URL")


def sap_http_auth() -> tuple[str, str]:
    return (env("SAP_USER"), env("SAP_PASSWD"))


def sap_client() -> str:
    return env("SAP_CLIENT")


def sap_configured() -> bool:
    """True if SAP HTTP is configured enough for outbound calls."""
    return bool(sap_http_url() and sap_http_auth()[0] and sap_http_auth()[1])


# --- Azure OpenAI ---


def azure_openai_key() -> str:
    return env("AZURE_OPENAI_API_KEY")


def azure_openai_endpoint() -> str:
    return env("AZURE_OPENAI_ENDPOINT")


def azure_openai_deployment() -> str:
    return env("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")


def azure_openai_fast_deployment() -> str:
    return env("AZURE_OPENAI_FAST_DEPLOYMENT_NAME") or azure_openai_deployment()


def azure_openai_map_filter_deployment() -> str:
    return env("AZURE_OPENAI_MAP_FILTER_DEPLOYMENT_NAME") or azure_openai_fast_deployment()


def azure_openai_embedding_deployment() -> str:
    return env("AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME", "text-embedding-3-small")


def azure_openai_api_version() -> str:
    return env("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")


def azure_openai_configured() -> bool:
    return bool(azure_openai_key() and azure_openai_endpoint())


# --- SAP ADT (optional; for adt-write) ---


def sap_adt_host() -> str:
    return env("SAP_ADT_HOST") or env("SAP_HTTP_URL", "").rstrip("/")


def sap_adt_user() -> str:
    return env("SAP_ADT_USER") or env("SAP_USER")


def sap_adt_password() -> str:
    return env("SAP_ADT_PASSWORD") or env("SAP_PASSWD")


def sap_adt_client() -> str:
    return env("SAP_ADT_CLIENT") or env("SAP_CLIENT", "200")


def sap_adt_language() -> str:
    return env("SAP_ADT_LANGUAGE", "EN")


def sap_adt_configured() -> bool:
    return bool(sap_adt_host() and sap_adt_user() and sap_adt_password())


# --- MCP (external SAP Docs / ADT tools) ---


def mcp_docs_url() -> str:
    """URL for SAP Docs/ABAP MCP server (DOCS_ABAP or DOCS_FULL)."""
    return env("EXTERNAL_SAP_MCP_DOCS_ABAP_URL") or env("EXTERNAL_SAP_MCP_DOCS_FULL_URL")


def mcp_adt_url() -> str:
    """URL for SAP ADT MCP server."""
    return env("EXTERNAL_SAP_MCP_ADT_URL")


def mcp_adt_tools_whitelist() -> str:
    """Comma-separated list of ADT tool names to expose (default: GetClass,GetTable)."""
    return env("EXTERNAL_SAP_MCP_ADT_TOOLS", "GetClass,GetTable")


def mcp_http_verify_ssl() -> bool:
    """Verify TLS for MCP HTTPS (default True).

    Set EXTERNAL_SAP_MCP_VERIFY_SSL=false when a corporate proxy uses a
    self-signed MITM cert (insecure; dev/trusted networks only).
    """
    raw = (os.getenv("EXTERNAL_SAP_MCP_VERIFY_SSL") or "").strip().lower()
    if raw in ("false", "0", "no", "off"):
        return False
    return True


def mcp_docs_configured() -> bool:
    """에이전트에 SAP Docs MCP 도구를 붙일 URL이 있는지."""
    return bool(mcp_docs_url().strip())


def mcp_adt_configured() -> bool:
    """에이전트에 ADT MCP(GetClass 등) URL이 있는지."""
    return bool(mcp_adt_url().strip())


# --- LLM / RAG budgets (tokens, retrieval, cache, graph limits) ---
# Defaults are conservative for cost/latency. See docs/LLM_BUDGETS.md at repo root.


def llm_code_review_max_tokens() -> int:
    return max(256, env_int("LLM_CODE_REVIEW_MAX_TOKENS", 2500))


def llm_code_review_temperature() -> float:
    return env_float("LLM_CODE_REVIEW_TEMPERATURE", 0.1)


def llm_agent_temperature() -> float:
    return env_float("LLM_AGENT_TEMPERATURE", 0.0)


def llm_agent_recursion_limit() -> int:
    """LangGraph ReAct max steps (tool loops). Higher = more cost/latency."""
    return max(5, env_int("LLM_AGENT_RECURSION_LIMIT", 25))


def llm_simple_chat_temperature() -> float:
    return env_float("LLM_SIMPLE_CHAT_TEMPERATURE", 0.2)


def llm_chat_rag_temperature() -> float:
    return env_float("LLM_CHAT_RAG_TEMPERATURE", 0.2)


def llm_rag_chain_temperature() -> float:
    return env_float("LLM_RAG_CHAIN_TEMPERATURE", 0.2)


def rag_default_k() -> int:
    """Default top-k chunks for retrieve / agent search_rag."""
    return max(1, min(50, env_int("RAG_DEFAULT_K", 5)))


def rag_query_max_k() -> int:
    """API hard cap for POST /api/rag/query/ k parameter."""
    return max(1, min(50, env_int("RAG_QUERY_MAX_K", 20)))


def mcp_rag_query_max_k() -> int:
    """Cap for MCP rag_ask / embedded RAG k."""
    return max(1, min(20, env_int("MCP_RAG_QUERY_MAX_K", 10)))


def chat_rag_cache_ttl_sec() -> int:
    """In-memory TTL for /api/chat/rag/ when use_cache=true."""
    return max(0, env_int("CHAT_RAG_CACHE_TTL_SEC", 300))


def analyze_graph_recursion_limit() -> int:
    """LangGraph deploy workflow recursion_limit."""
    return max(10, env_int("ANALYZE_GRAPH_RECURSION_LIMIT", 22))


def deploy_research_rag_k() -> int:
    """배포 심의 Researcher 노드 Chroma top-k (CRAG 1단계)."""
    return max(1, min(20, env_int("DEPLOY_RESEARCH_RAG_K", 6)))


def deploy_research_rag_enabled() -> bool:
    """배포 심의 Chroma 벡터 검색(Researcher). false면 검색·CRAG 판정 생략."""
    return env_bool("DEPLOY_RESEARCH_RAG_ENABLED", True)


def deploy_crag_judge_enabled() -> bool:
    """CRAG 관련성 LLM 판정·쿼리 재작성. 벡터 RAG 켜져 있을 때만 적용."""
    return env_bool("DEPLOY_CRAG_JUDGE_ENABLED", True)


def deploy_self_rag_enabled() -> bool:
    """배포 심의 아키텍트 직후 Self-RAG(근거 검증·1회 보정). false면 생략."""
    return env_bool("DEPLOY_SELF_RAG_ENABLED", True)


def deploy_graph_rag_enabled() -> bool:
    """배포 심의 GraphRAG(3단계): TR 시드 기준 DependencySnapshot 간선 수집."""
    return env_bool("DEPLOY_GRAPH_RAG_ENABLED", True)


def deploy_graph_rag_max_edges() -> int:
    return max(5, min(500, env_int("DEPLOY_GRAPH_RAG_MAX_EDGES", 100)))


def deploy_graph_rag_max_hops() -> int:
    """0=시드 직접 연결 간선만, 1=한 번 노드 확장 후 추가 간선(상한 내)."""
    return max(0, min(3, env_int("DEPLOY_GRAPH_RAG_MAX_HOPS", 1)))


def deploy_graph_rag_max_seeds() -> int:
    """TR에서 뽑는 시드 오브젝트명 상한(DB __in 부담 완화)."""
    return max(5, min(300, env_int("DEPLOY_GRAPH_RAG_MAX_SEEDS", 100)))


def llm_map_filter_max_tokens() -> int:
    return max(256, env_int("LLM_MAP_FILTER_MAX_TOKENS", 2500))


def llm_map_filter_temperature() -> float:
    return env_float("LLM_MAP_FILTER_TEMPERATURE", 0.1)


def llm_usage_tracking_enabled() -> bool:
    """OpenAI callback으로 토큰 집계·대시보드용. False면 콜백 생략."""
    return env_bool("LLM_USAGE_TRACKING_ENABLED", True)


def llm_usage_recent_max() -> int:
    """대시보드 API가 반환하는 최근 이벤트 최대 개수 (DB 조회 LIMIT)."""
    return max(10, min(5000, env_int("LLM_USAGE_RECENT_MAX", 200)))


def usage_stats_reset_allowed() -> bool:
    """POST /api/usage-stats/reset/ 허용 (개발용)."""
    return env_bool("USAGE_STATS_ALLOW_RESET", False)
