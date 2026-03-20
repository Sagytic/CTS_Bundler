"""
Request correlation ID + API request timing for operations / log aggregation.

- Generates or forwards X-Request-ID (client may send HTTP_X_REQUEST_ID).
- Attaches request.request_id for use in views (e.g. LLM span logs).
- Logs one line per /api/* request with duration and status (structured key=value).
"""
from __future__ import annotations

import logging
import time
import uuid

logger = logging.getLogger("cts.request")

# Paths to skip high-volume noise (optional tuning)
_SKIP_PREFIXES: tuple[str, ...] = ("/api/admin/",)


class RequestContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        header_rid = request.META.get("HTTP_X_REQUEST_ID", "").strip()
        rid = header_rid or str(uuid.uuid4())
        request.request_id = rid

        start = time.perf_counter()
        response = self.get_response(request)
        duration_ms = (time.perf_counter() - start) * 1000

        path = request.path or ""
        if path.startswith("/api/") and not any(
            path.startswith(p) for p in _SKIP_PREFIXES
        ):
            status = getattr(response, "status_code", 0)
            logger.info(
                "api.request request_id=%s method=%s path=%s status=%s duration_ms=%.2f",
                rid,
                request.method,
                path,
                status,
                duration_ms,
            )

        if response is not None and hasattr(response, "__setitem__"):
            response["X-Request-ID"] = rid
        return response
