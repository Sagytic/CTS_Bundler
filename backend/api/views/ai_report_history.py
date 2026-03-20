"""저장된 AI 코드 리뷰·배포 리포트 조회 API."""
from __future__ import annotations

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.models import CodeReviewRecord, DeployReportRecord


def _limit(request: Request, default: int = 20, cap: int = 100) -> int:
    try:
        n = int(request.query_params.get("limit", default))
    except ValueError:
        n = default
    return max(1, min(n, cap))


class CodeReviewHistoryListView(APIView):
    """GET /api/code-review-history/?limit=20"""

    def get(self, request: Request) -> Response:
        qs = CodeReviewRecord.objects.all()[: _limit(request)]
        out = []
        for r in qs:
            prev = r.ai_result or ""
            if len(prev) > 400:
                prev = prev[:400] + "…"
            out.append(
                {
                    "id": r.id,
                    "created_at": r.created_at.isoformat(),
                    "request_id": r.request_id,
                    "user_id": r.user_id,
                    "obj_name": r.obj_name,
                    "streamed": r.streamed,
                    "preview": prev,
                }
            )
        return Response(out)


class CodeReviewHistoryDetailView(APIView):
    """GET /api/code-review-history/<id>/"""

    def get(self, request: Request, pk: int) -> Response:
        r = CodeReviewRecord.objects.filter(pk=pk).first()
        if not r:
            return Response({"error": "not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(
            {
                "id": r.id,
                "created_at": r.created_at.isoformat(),
                "request_id": r.request_id,
                "user_id": r.user_id,
                "obj_name": r.obj_name,
                "abap_code": r.abap_code,
                "requirement_spec": r.requirement_spec,
                "ai_result": r.ai_result,
                "streamed": r.streamed,
            }
        )


class DeployReportHistoryListView(APIView):
    """GET /api/deploy-report-history/?limit=20"""

    def get(self, request: Request) -> Response:
        qs = DeployReportRecord.objects.all()[: _limit(request)]
        out = []
        for r in qs:
            prev = r.final_report or ""
            if len(prev) > 500:
                prev = prev[:500] + "…"
            out.append(
                {
                    "id": r.id,
                    "created_at": r.created_at.isoformat(),
                    "request_id": r.request_id,
                    "user_id": r.user_id,
                    "selected_trs": r.selected_trs,
                    "preview": prev,
                    "extra": r.extra,
                }
            )
        return Response(out)


class DeployReportHistoryDetailView(APIView):
    """GET /api/deploy-report-history/<id>/"""

    def get(self, request: Request, pk: int) -> Response:
        r = DeployReportRecord.objects.filter(pk=pk).first()
        if not r:
            return Response({"error": "not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(
            {
                "id": r.id,
                "created_at": r.created_at.isoformat(),
                "request_id": r.request_id,
                "user_id": r.user_id,
                "user_input": r.user_input,
                "selected_trs": r.selected_trs,
                "final_report": r.final_report,
                "extra": r.extra,
            }
        )
