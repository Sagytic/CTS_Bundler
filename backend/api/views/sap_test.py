"""SAP connectivity test API."""
from __future__ import annotations

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.sap_client import fetch_recent_transports_via_http


class SapTestView(APIView):
    """GET /api/sap-test/. Returns SAP connection status and sample transports."""

    def get(self, request: Request) -> Response:
        result = fetch_recent_transports_via_http()
        if result.get("status") == "success":
            return Response(
                {"message": "SAP HTTP 연결 성공!", "transports": result.get("data", [])},
                status=status.HTTP_200_OK,
            )
        return Response(
            {"message": "SAP 연결 실패", "error": result.get("message", "unknown")},
            status=status.HTTP_502_BAD_GATEWAY,
        )
