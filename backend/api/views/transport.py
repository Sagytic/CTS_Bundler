"""Transport list API: SAP TR list by user_id."""
from __future__ import annotations

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.sap_client import fetch_recent_transports_via_http

# Fallback when SAP is unavailable (e.g. dev without SAP)
MOCK_TRANSPORTS_TEMPLATE = [
    {
        "TRKORR": "EDAK900101",
        "AS4TEXT": "[{user_id}] MM 발주서 승인 오류 수정",
        "TRFUNCTION": "K",
        "TRSTATUS": "D",
        "AS4DATE": "20260309",
        "AS4TIME": "093000",
    },
    {
        "TRKORR": "EDAK900102",
        "AS4TEXT": "[{user_id}] FI 모듈 전표 전송 로직 개선",
        "TRFUNCTION": "K",
        "TRSTATUS": "D",
        "AS4DATE": "20260308",
        "AS4TIME": "141500",
    },
]


class TRListView(APIView):
    """GET /api/transports/?user_id=<sap_user_id>. Returns list of transports."""

    def get(self, request: Request) -> Response:
        user_id = (request.query_params.get("user_id") or "").strip()
        if not user_id:
            return Response(
                {"error": "user_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = fetch_recent_transports_via_http(user_id=user_id)

        if result.get("status") == "success":
            data = result.get("data") or []
            return Response({"transports": data[:50]}, status=status.HTTP_200_OK)

        # Fallback mock for dev when SAP is not configured or fails
        mock = [
            {**t, "AS4TEXT": t["AS4TEXT"].format(user_id=user_id)}
            for t in MOCK_TRANSPORTS_TEMPLATE
        ]
        return Response({"transports": mock}, status=status.HTTP_200_OK)
