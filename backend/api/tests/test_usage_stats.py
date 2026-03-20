"""LLM usage stats API."""
from __future__ import annotations

import pytest
from django.test import Client


@pytest.mark.django_db
def test_usage_stats_get_shape():
    c = Client()
    r = c.get("/api/usage-stats/")
    assert r.status_code == 200
    data = r.json()
    assert "summary" in data
    assert "by_operation" in data
    assert "recent" in data
    assert "server_started_at" in data
    s = data["summary"]
    assert "total_calls" in s
    assert "total_prompt_tokens" in s
    assert "total_completion_tokens" in s


@pytest.mark.django_db
def test_usage_stats_reset_forbidden_by_default():
    c = Client()
    r = c.post("/api/usage-stats/reset/")
    assert r.status_code == 403


@pytest.mark.django_db
def test_usage_stats_persisted_via_db():
    from api.usage_metrics import record_llm_usage

    record_llm_usage(
        "pytest_op",
        "req-1",
        prompt_tokens=10,
        completion_tokens=20,
        total_tokens=30,
        duration_ms=12.5,
        ok=True,
        extra={"k": "v"},
    )
    c = Client()
    r = c.get("/api/usage-stats/")
    assert r.status_code == 200
    data = r.json()
    assert data["summary"]["total_calls"] >= 1
    assert "pytest_op" in data["by_operation"]
    assert data["by_operation"]["pytest_op"]["total_tokens"] == 30
    recent_ops = [row["operation"] for row in data["recent"]]
    assert "pytest_op" in recent_ops
