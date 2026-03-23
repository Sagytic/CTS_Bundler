"""Ticket info and ticket mapping APIs."""
from __future__ import annotations

import logging
from typing import Optional

import requests
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.config import sap_client, sap_http_auth, sap_http_url
from api.models import TicketMapping

_logger = logging.getLogger("cts.ai")

SAP_TIMEOUT_GET_CODE = 10


class TicketInfoView(APIView):
    """GET /api/ticket-info/?trkorr=...&objName=.... Returns ticket_id, description, abap_code."""

    def get(self, request: Request) -> Response:
        trkorr = (request.GET.get("trkorr") or "").strip()
        obj_name = (request.GET.get("objName") or "").strip()

        if not trkorr:
            return Response(
                {"error": "trkorr 쿼리 파라미터가 필요합니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            ticket = TicketMapping.objects.get(target_key=trkorr)
            ticket_id = ticket.ticket_id
            description = ticket.description
        except TicketMapping.DoesNotExist:
            ticket_id = "미매핑 (수동입력 필요)"
            description = "해당 CTS 번호에 매핑된 현업 요구사항 티켓이 DB에 없습니다."

        abap_code_snippet = self._fetch_abap_code(obj_name)
        return Response(
            {
                "ticket_id": ticket_id,
                "description": description,
                "abap_code": abap_code_snippet,
            },
            status=status.HTTP_200_OK,
        )

    def _fetch_abap_code(self, obj_name: str) -> str:
        url = sap_http_url()
        user, password = sap_http_auth()
        client = sap_client()
        if not url or not user or not password:
            return "소스코드를 가져오는 중 오류가 발생했습니다. (SAP 미설정)"

        try:
            full_url = f"{url.rstrip('/')}?sap-client={client}&action=get_code&obj_name={obj_name}"
            response = requests.get(
                full_url,
                auth=(user, password),
                timeout=SAP_TIMEOUT_GET_CODE,
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("source_code", "코드를 반환받지 못했습니다.")
            _logger.error("SAP connection failed: HTTP %s", response.status_code)
            return f"SAP 연결 실패: HTTP {response.status_code}"
        except requests.exceptions.RequestException as e:
            _logger.exception("SAP communication error: %s", e)
            return "SAP 통신 오류가 발생했습니다. 상세 내용은 서버 로그를 확인하세요."


class TicketMappingUpsertView(APIView):
    """POST /api/ticket-mapping/. Create or update TR ↔ ticket mapping."""

    def post(self, request: Request) -> Response:
        trkorr = (request.data.get("trkorr") or "").strip()
        if not trkorr:
            return Response(
                {"error": "trkorr는 필수입니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ticket_id = (request.data.get("ticket_id") or "미매핑").strip() or "미매핑"
        description = (request.data.get("description") or "").strip()

        mapping, _ = TicketMapping.objects.update_or_create(
            target_key=trkorr,
            defaults={"ticket_id": ticket_id, "description": description},
        )
        return Response(
            {
                "ok": True,
                "ticket_id": mapping.ticket_id,
                "description": mapping.description,
            },
            status=status.HTTP_200_OK,
        )
