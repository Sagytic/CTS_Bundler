"""
MCP (Model Context Protocol) server for CTS Bundler.
Exposes tools so AI clients (e.g. Cursor, Claude Desktop) can query transports, dependency graph, tickets, and RAG.

Run (stdio, for Cursor):
  cd backend && python -m api.mcp_server

Run (Streamable HTTP, optional):
  cd backend && python -m api.mcp_server --transport streamable-http --port 8020
"""
import sys
from pathlib import Path

# Bootstrap Django before importing models/sap_client
_backend_root = Path(__file__).resolve().parent
if str(_backend_root) not in sys.path:
    sys.path.insert(0, str(_backend_root))
sys.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

import django
django.setup()

# Now safe to import app code
from api.config import mcp_rag_query_max_k
from api.models import DependencySnapshot, TicketMapping
from api.sap_client import fetch_recent_transports_via_http, filter_main_transports


def _get_mcp():
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError:
        from fastmcp import FastMCP
    return FastMCP(
        "CTS Bundler",
        description="SAP CTS Bundler: TR 목록, 종속성 그래프, 티켓 매핑, RAG 검색",
    )


mcp = _get_mcp()


@mcp.tool()
def list_transports(user_id: str) -> str:
    """사용자별 최근 메인 TR 목록을 조회합니다(CTS Analyzer와 동일: Workbench K / Customizing W만, 태스크·하위 TR 제외). user_id는 SAP 사번(예: 11355)입니다."""
    result = fetch_recent_transports_via_http(user_id=user_id)
    if result["status"] != "success":
        return f"TR 목록 조회 실패: {result.get('message', 'unknown')}"
    raw = result.get("data", [])
    data = filter_main_transports(raw if isinstance(raw, list) else [])
    lines = [f"- {tr.get('TRKORR', tr.get('trkorr', ''))}: {tr.get('AS4TEXT', tr.get('as4text', ''))}" for tr in data[:50]]
    return "TR 목록:\n" + "\n".join(lines) if lines else "조회된 TR이 없습니다."


@mcp.tool()
def get_dependency_edges(target_obj: str, limit: int = 100) -> str:
    """지정한 SAP 오브젝트(프로그램/테이블명)에 대한 종속성 관계를 DB에서 조회합니다. target_obj는 대문자(예: ZMMR0030)로 주세요."""
    target = (target_obj or "").strip().upper()
    if not target:
        return "target_obj를 입력하세요."
    direct = list(DependencySnapshot.objects.filter(source_obj=target).values_list("source_obj", "target_obj", "target_group")[:limit])
    backward = list(DependencySnapshot.objects.filter(target_obj=target).values_list("source_obj", "target_obj", "target_group")[:limit])
    lines = [f"{s} → {t} (group {g})" for s, t, g in (direct + backward)]
    return f"종속성 ({target}):\n" + "\n".join(lines) if lines else f"[{target}]에 대한 종속성 데이터가 없습니다."


@mcp.tool()
def get_ticket_mapping(trkorr: str) -> str:
    """list_transports로 받은 실제 TRKORR만 사용하세요. TRK123456 등 임의 번호는 금지. JIRA 티켓·요구사항 설명을 조회합니다."""
    key = (trkorr or "").strip()
    if not key:
        return "trkorr를 입력하세요."
    try:
        t = TicketMapping.objects.get(target_key=key)
        return f"티켓: {t.ticket_id}\n요구사항: {t.description}"
    except TicketMapping.DoesNotExist:
        return f"[{key}]에 대한 티켓 매핑이 없습니다."


@mcp.tool()
def search_rag(query: str, k: int = 5) -> str:
    """RAG 지식베이스에서 시맨틱 검색 후 관련 문서를 반환합니다. (DB 종속성·티켓 매핑 등이 인덱싱되어 있어야 함)."""
    from api.rag import services
    query = (query or "").strip()
    if not query:
        return "query를 입력하세요."
    try:
        results = services.retrieve(query, k=min(k, mcp_rag_query_max_k()))
        if not results:
            return "관련 문서가 없습니다. 먼저 POST /api/rag/ingest/ 로 데이터를 넣어주세요."
        lines = [f"[{i+1}] (score {s:.3f}) {d.page_content}" for i, (d, s) in enumerate(results)]
        return "검색 결과:\n" + "\n".join(lines)
    except Exception as e:
        return f"RAG 검색 오류: {e}"


@mcp.tool()
def rag_ask(query: str, k: int = 5) -> str:
    """RAG로 질의한 뒤 LLM이 참고 문서를 바탕으로 답변을 생성합니다."""
    from api.rag import services
    query = (query or "").strip()
    if not query:
        return "query를 입력하세요."
    try:
        return services.rag_chain_invoke(query, k=min(k, mcp_rag_query_max_k()))
    except Exception as e:
        return f"RAG 답변 생성 오류: {e}"


def main():
    import argparse
    p = argparse.ArgumentParser(
        description="CTS Bundler MCP Server. stdio=Cursor 전용, streamable-http/sse=외부 연동용.",
    )
    p.add_argument(
        "--transport",
        default="stdio",
        choices=["stdio", "streamable-http", "sse"],
        help="stdio: Cursor만. streamable-http/sse: 외부 클라이언트 HTTP 접속용.",
    )
    p.add_argument(
        "--host",
        default="127.0.0.1",
        help="HTTP 모드에서 바인드 주소. 외부에서 접속하려면 0.0.0.0",
    )
    p.add_argument("--port", type=int, default=8020, help="HTTP 모드 포트")
    p.add_argument("--path", default="/mcp", help="HTTP 모드 경로")
    args = p.parse_args()

    if args.transport == "stdio":
        mcp.run(transport="stdio")
    else:
        print(f"MCP 서버 (외부 연동): http://{args.host}:{args.port}{args.path}", file=sys.stderr)
        mcp.run(
            transport=args.transport,
            host=args.host,
            port=args.port,
            path=args.path,
        )


if __name__ == "__main__":
    main()
