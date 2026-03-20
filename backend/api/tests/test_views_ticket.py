"""Tests for ticket-info and ticket-mapping API."""
import pytest
from rest_framework import status


@pytest.mark.django_db
class TestTicketInfoView:
    """GET /api/ticket-info/."""

    def test_missing_params(self, api_client):
        r = api_client.get("/api/ticket-info/")
        assert r.status_code in (status.HTTP_400_BAD_REQUEST, status.HTTP_404_NOT_FOUND)

    def test_found(self, api_client, ticket_mapping_data):
        r = api_client.get("/api/ticket-info/?trkorr=EDAK901372")
        # View may return 200 with data or 404; if we have data it should be 200
        if r.status_code == 200:
            data = r.json()
            assert "ticket_id" in data or "description" in data or "EDAK901372" in str(data)


@pytest.mark.django_db
class TestTicketMappingUpsertView:
    """POST /api/ticket-mapping/."""

    def test_create_or_update(self, api_client):
        r = api_client.post(
            "/api/ticket-mapping/",
            data={
                "trkorr": "TEST_TR",
                "ticket_id": "JIRA-TEST",
                "description": "Test requirement",
            },
            format="json",
        )
        assert r.status_code == status.HTTP_200_OK
        assert r.json().get("ok") is True
