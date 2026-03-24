"""
SAP HTTP client for CTS API: transports, dependency graph, object usage.

All endpoints use HTTP Basic Auth and query params. Config from api.config.
"""
from __future__ import annotations

from typing import Any, Optional

import requests
from requests.auth import HTTPBasicAuth

from api.config import sap_client, sap_http_auth, sap_http_url

SAP_TIMEOUT_TRANSPORTS = 10
SAP_TIMEOUT_DEPENDENCY = 15
SAP_TIMEOUT_OBJECT_USAGE = 60


def filter_main_transports(transports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    CTS Analyzer / 프론트 filterMainTransports와 동일: 메인(부모) TR만 유지.

    SAP에서 TRFUNCTION(또는 trfunction)이 K(Workbench 요청) 또는 W(Customizing 요청)인
    행만 남기고, 태스크/하위 TR 등은 제외합니다.
    """
    out: list[dict[str, Any]] = []
    for tr in transports:
        if not isinstance(tr, dict):
            continue
        t = str(tr.get("TRFUNCTION") or tr.get("trfunction") or "").strip().upper()
        if t in ("K", "W"):
            out.append(tr)
    return out


def fetch_recent_transports_via_http(user_id: Optional[str] = None) -> dict[str, Any]:
    """
    Fetch recent transport list from SAP CTS API.

    Returns:
        {"status": "success", "data": [...]} or {"status": "error", "message": "..."}
    """
    url = sap_http_url()
    user, password = sap_http_auth()
    client = sap_client()

    if not url or not user or not password:
        return {"status": "error", "message": "SAP HTTP not configured (SAP_HTTP_URL, SAP_USER, SAP_PASSWD)"}

    params: dict[str, Any] = {"sap-client": client}
    if user_id:
        params["user_id"] = user_id

    try:
        response = requests.get(
            url,
            auth=HTTPBasicAuth(user, password),
            params=params,
            timeout=SAP_TIMEOUT_TRANSPORTS,
        )
        if response.status_code == 200:
            return {"status": "success", "data": response.json()}
        return {
            "status": "error",
            "message": f"HTTP {response.status_code}: {response.text[:500]}",
        }
    except requests.exceptions.RequestException as e:
        import logging
        logging.getLogger("cts.ai").exception("SAP client error")
        return {"status": "error", "message": "SAP 서버 통신 중 오류가 발생했습니다. 상세 내용은 서버 로그를 확인하세요."}


def fetch_dependency_graph_via_http(target_obj: str = "") -> dict[str, Any]:
    """
    Fetch dependency graph from SAP (action=dependency).

    Returns:
        {"status": "success", "data": {...}} or {"status": "error", "message": "..."}
    """
    url = sap_http_url()
    user, password = sap_http_auth()
    client = sap_client()

    if not url or not user or not password:
        return {"status": "error", "message": "SAP HTTP not configured"}

    params: dict[str, Any] = {"sap-client": client, "action": "dependency"}
    if target_obj:
        params["target_obj"] = target_obj.strip()

    try:
        response = requests.get(
            url,
            auth=HTTPBasicAuth(user, password),
            params=params,
            timeout=SAP_TIMEOUT_DEPENDENCY,
        )
        if response.status_code == 200:
            return {"status": "success", "data": response.json()}
        return {
            "status": "error",
            "message": f"HTTP {response.status_code}: {response.text[:500]}",
        }
    except requests.exceptions.RequestException as e:
        import logging
        logging.getLogger("cts.ai").exception("SAP client error")
        return {"status": "error", "message": "SAP 서버 통신 중 오류가 발생했습니다. 상세 내용은 서버 로그를 확인하세요."}


def fetch_object_usage_via_http(trkorr: Optional[str]) -> dict[str, Any]:
    """
    Fetch TR object usage (CALL/SUBMIT/MODIFY/...) from SAP (action=object_usage).

    Returns:
        {"status": "success", "data": {...}} or {"status": "error", "message": "..."}
    """
    url = sap_http_url()
    user, password = sap_http_auth()
    client = sap_client()

    if not url or not user or not password:
        return {"status": "error", "message": "SAP HTTP not configured"}

    params: dict[str, Any] = {
        "sap-client": client,
        "action": "object_usage",
        "trkorr": (trkorr or "").strip(),
    }

    try:
        response = requests.get(
            url,
            auth=HTTPBasicAuth(user, password),
            params=params,
            timeout=SAP_TIMEOUT_OBJECT_USAGE,
        )
        if response.status_code == 200:
            return {"status": "success", "data": response.json()}
        return {
            "status": "error",
            "message": f"HTTP {response.status_code}: {response.text[:500]}",
        }
    except requests.exceptions.RequestException as e:
        import logging
        logging.getLogger("cts.ai").exception("SAP client error")
        return {"status": "error", "message": "SAP 서버 통신 중 오류가 발생했습니다. 상세 내용은 서버 로그를 확인하세요."}
