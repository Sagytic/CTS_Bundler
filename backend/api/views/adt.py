"""ADT write API: create/update ABAP objects via ADT (abap_adt_py)."""
from __future__ import annotations

import logging
import re
import sys
from pathlib import Path

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.config import (
    sap_adt_client,
    sap_adt_host,
    sap_adt_language,
    sap_adt_password,
    sap_adt_user,
)


_logger = logging.getLogger("cts.ai")

_ADT_INSTALL_HINT = (
    "SAP ADT 쓰기에 필요한 Python 패키지가 없습니다. "
    "backend 가상환경에서 실행: pip install abap-adt-py"
)


def _get_adt_client():
    """Return AdtClient from abap_adt_py (optional local site-packages fallback)."""
    try:
        from abap_adt_py.adt_client import AdtClient
    except ImportError:
        backend_dir = Path(__file__).resolve().parent.parent.parent
        side_project = backend_dir.parent
        adt_site = side_project / "ABAP" / "adt-py-test" / "venv" / "Lib" / "site-packages"
        if adt_site.is_dir() and str(adt_site) not in sys.path:
            sys.path.insert(0, str(adt_site))
        try:
            from abap_adt_py.adt_client import AdtClient
        except ImportError as e:
            raise ImportError(_ADT_INSTALL_HINT) from e

    host = sap_adt_host()
    user = sap_adt_user()
    password = sap_adt_password()
    client = sap_adt_client()
    lang = sap_adt_language()
    if not host or not user or not password:
        raise ValueError(
            "SAP ADT not configured. Set SAP_ADT_HOST, SAP_ADT_USER, SAP_ADT_PASSWORD (or SAP_HTTP_URL, SAP_USER, SAP_PASSWD)."
        )
    return AdtClient(sap_host=host, username=user, password=password, client=client, language=lang)


def _adt_fetch_csrf_token(adt):
    """라이브러리 login() 대신 CSRF 토큰만 직접 조회. X-CSRF-Token: Fetch 사용, 헤더·본문 모두 확인."""
    url = adt.sap_host.rstrip("/") + "/sap/bc/adt/compatibility/graph"
    params = {}
    if getattr(adt, "client", None):
        params["sap-client"] = adt.client
    if getattr(adt, "language", None):
        params["sap-language"] = adt.language
    headers = {"X-CSRF-Token": "Fetch", "Accept": "*/*", "Cache-Control": "no-cache"}
    resp = adt.session.get(url, headers=headers, params=params, timeout=30)
    if resp.status_code != 200:
        raise Exception(f"CSRF 토큰 요청 실패: HTTP {resp.status_code}\n{resp.text[:500]}")
    token = resp.headers.get("x-csrf-token") or resp.headers.get("X-CSRF-Token")
    if not token and resp.text:
        m = re.search(r'["\']?token["\']?\s*[:=]\s*["\']([^"\']+)["\']', resp.text, re.I)
        if m:
            token = m.group(1)
    if not token:
        raise Exception("CSRF token not found in response headers or body. (SAP가 헤더에 x-csrf-token을 반환하지 않았습니다.)")
    adt.csrf_token = token


class AdtWriteView(APIView):
    """POST /api/adt-write/. Write refactored ABAP source via ADT (lock → set_object_source → unlock)."""

    def post(self, request: Request) -> Response:
        obj_name = (
            request.data.get("objName") or request.data.get("obj_name") or ""
        ).strip()
        obj_type = (
            request.data.get("objType") or request.data.get("obj_type") or "PROG"
        ).strip().upper()
        new_source = request.data.get("newSource") or request.data.get("new_source") or ""
        trkorr = (
            request.data.get("trkorr") or request.data.get("tr_number") or ""
        ).strip()

        if not obj_name:
            return Response(
                {"error": "objName은 필수입니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not trkorr:
            return Response(
                {"error": "trkorr(TR 번호)는 필수입니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if obj_type not in ("PROG", "CLAS"):
            return Response(
                {"error": "objType은 PROG 또는 CLAS만 지원합니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        name_lower = obj_name.lower()
        if obj_type == "PROG":
            object_uri = f"/sap/bc/adt/programs/programs/{name_lower}/source/main"
        else:
            object_uri = f"/sap/bc/adt/oo/classes/{name_lower}/source/main"
        save_uri = f"{object_uri}?corrNr={trkorr}"
        lock_handle = None
        adt = None
        try:
            adt = _get_adt_client()
            _adt_fetch_csrf_token(adt)
            lock_handle = adt.lock(object_uri)
            adt.set_object_source(save_uri, new_source, lock_handle=lock_handle)
            adt.unlock(object_uri, lock_handle=lock_handle)
            return Response(
                {"ok": True, "message": f"{obj_name} 소스가 TR {trkorr}로 저장되었습니다."},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            _logger.exception("ADT write error: %s", e)
            if adt and lock_handle:
                try:
                    adt.unlock(object_uri, lock_handle=lock_handle)
                except Exception:
                    pass
            return Response(
                {"error": "SAP ADT 통신 중 오류가 발생했습니다. 상세 내용은 서버 로그를 확인하세요."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
