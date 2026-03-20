"""Saved code review / deploy report list APIs."""
import pytest
from rest_framework import status


@pytest.mark.django_db
def test_code_review_history_list_empty(api_client):
    r = api_client.get("/api/code-review-history/")
    assert r.status_code == status.HTTP_200_OK
    assert r.json() == []


@pytest.mark.django_db
def test_deploy_report_history_list_empty(api_client):
    r = api_client.get("/api/deploy-report-history/")
    assert r.status_code == status.HTTP_200_OK
    assert r.json() == []
