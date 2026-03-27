"""Login API: simple session-based auth."""
from __future__ import annotations

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView


class LoginView(APIView):
    """POST /api/login/ with {"user_id": "..."}. Sets session."""

    def post(self, request: Request) -> Response:
        user_id = (request.data.get("user_id") or "").strip()
        if not user_id:
            return Response(
                {"error": "user_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        request.session["user_id"] = user_id
        return Response({"message": "Logged in"}, status=status.HTTP_200_OK)
