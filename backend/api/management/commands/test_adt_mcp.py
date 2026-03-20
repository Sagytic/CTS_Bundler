"""
ADT MCP 연동 테스트.

사용법 (backend 폴더에서):
  python manage.py test_adt_mcp

필요 조건:
  - backend/.env 에 EXTERNAL_SAP_MCP_ADT_URL 이 설정되어 있어야 함.
  - ADT MCP 서버가 해당 URL에서 HTTP(Streamable HTTP)로 떠 있어야 함.
    (mario-andreschak/mcp-abap-adt 는 기본이 stdio 이므로, HTTP 지원 버전 사용 또는
     별도 HTTP 래퍼가 필요함. docs/EXTERNAL_SAP_MCP.md 참고.)
"""
import os

from django.core.management.base import BaseCommand

from dotenv import load_dotenv
from pathlib import Path

# backend/.env 로드 (api/management/commands -> backend)
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(_BACKEND_DIR / ".env")


def _run_async(coro):
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    if loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(asyncio.run, coro).result()
    return loop.run_until_complete(coro)


class Command(BaseCommand):
    help = "ADT MCP(GetClass, GetTable) 연동 테스트. EXTERNAL_SAP_MCP_ADT_URL 이 설정되어 있어야 함."

    def add_arguments(self, parser):
        parser.add_argument(
            "--class",
            dest="class_name",
            default="SAPMV45A",
            help="GetClass 테스트에 쓸 클래스명 (기본: SAPMV45A)",
        )
        parser.add_argument(
            "--table",
            dest="table_name",
            default="MARA",
            help="GetTable 테스트에 쓸 테이블명 (기본: MARA)",
        )

    def handle(self, *args, **options):
        url = os.getenv("EXTERNAL_SAP_MCP_ADT_URL", "").strip()
        if not url:
            self.stdout.write(self.style.WARNING(
                "EXTERNAL_SAP_MCP_ADT_URL 이 backend/.env 에 없습니다.\n"
                "1) ADT MCP를 HTTP(Streamable HTTP)로 띄운 뒤\n"
                "2) backend/.env 에 예: EXTERNAL_SAP_MCP_ADT_URL=http://127.0.0.1:8021/mcp 추가 후\n"
                "   다시 python manage.py test_adt_mcp 를 실행하세요."
            ))
            return

        from api.mcp_client import _call_remote_tool, _fetch_remote_tools

        self.stdout.write(f"ADT MCP URL: {url}\n")

        # 1) 도구 목록 조회
        self.stdout.write("도구 목록 조회 중...")
        tools = _run_async(_fetch_remote_tools(url))
        if not tools:
            self.stdout.write(self.style.ERROR(
                "연결 실패 또는 도구 목록이 비어 있습니다. "
                "ADT MCP가 해당 URL에서 떠 있는지, 전송 방식이 Streamable HTTP인지 확인하세요."
            ))
            return
        self.stdout.write(self.style.SUCCESS(f"  사용 가능 도구: {[t['name'] for t in tools]}\n"))

        # 2) GetClass 테스트
        class_name = options.get("class_name") or "SAPMV45A"
        self.stdout.write(f"GetClass({class_name}) 호출 중...")
        try:
            out = _run_async(_call_remote_tool(url, "GetClass", {"class_name": class_name}))
            self.stdout.write(out[:2000] + ("..." if len(out) > 2000 else ""))
            self.stdout.write("")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  오류: {e}\n"))

        # 3) GetTable 테스트
        table_name = options.get("table_name") or "MARA"
        self.stdout.write(f"GetTable({table_name}) 호출 중...")
        try:
            out = _run_async(_call_remote_tool(url, "GetTable", {"table_name": table_name}))
            self.stdout.write(out[:2000] + ("..." if len(out) > 2000 else ""))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  오류: {e}\n"))

        self.stdout.write(self.style.SUCCESS("테스트 완료."))
