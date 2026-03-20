"""LLM token usage dashboard API (DB-backed aggregates)."""
from __future__ import annotations

from django.conf import settings
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.config import usage_stats_reset_allowed
from api.usage_metrics import reset_all, snapshot


class LLMUsageStatsView(APIView):
    """
    GET /api/usage-stats/ — 누적 토큰·최근 호출 목록 (SQLite 등 DB 영속).
    POST /api/usage-stats/reset/ — 카운터 초기화 (DEBUG 또는 USAGE_STATS_ALLOW_RESET=1).
    """

    def get(self, request: Request) -> Response:
        return Response(snapshot(), status=status.HTTP_200_OK)


class LLMUsageStatsResetView(APIView):
    def post(self, request: Request) -> Response:
        if not (settings.DEBUG or usage_stats_reset_allowed()):
            return Response(
                {"detail": "reset not allowed"},
                status=status.HTTP_403_FORBIDDEN,
            )
        reset_all()
        return Response({"ok": True}, status=status.HTTP_200_OK)
