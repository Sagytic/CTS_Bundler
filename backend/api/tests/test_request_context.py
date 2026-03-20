"""Request correlation ID middleware."""
from __future__ import annotations

import pytest
from django.test import Client


@pytest.mark.django_db
def test_x_request_id_generated_on_api():
    c = Client()
    r = c.post("/api/chat/", {}, content_type="application/json")
    assert r.status_code == 400
    rid = r.get("X-Request-ID") or r.headers.get("X-Request-ID")
    assert rid and len(str(rid)) >= 8


@pytest.mark.django_db
def test_x_request_id_forwarded_from_client():
    c = Client()
    incoming = "test-req-id-0001"
    r = c.post(
        "/api/chat/",
        {},
        content_type="application/json",
        HTTP_X_REQUEST_ID=incoming,
    )
    assert r.status_code == 400
    out = r.get("X-Request-ID") or r.headers.get("X-Request-ID")
    assert out == incoming
