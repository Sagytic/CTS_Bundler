"""Tests for dependency and dependency-edges API."""
import pytest
from rest_framework import status

from api.models import DependencySnapshot


@pytest.mark.django_db
class TestDependencyEdgesView:
    """GET /api/dependency-edges/."""

    def test_missing_target_obj(self, api_client):
        r = api_client.get("/api/dependency-edges/")
        assert r.status_code == status.HTTP_400_BAD_REQUEST
        assert "target_obj" in (r.json() or {}).get("error", "")

    def test_empty_result(self, api_client):
        r = api_client.get("/api/dependency-edges/?target_obj=NONEXISTENT")
        assert r.status_code == status.HTTP_200_OK
        data = r.json()
        assert data["target_obj"] == "NONEXISTENT"
        assert data["calls"] == []
        assert data["called_by"] == []
        assert "없음" in data["text"]

    def test_with_data(self, api_client, dependency_snapshot_data):
        r = api_client.get("/api/dependency-edges/?target_obj=ZMMR0030")
        assert r.status_code == status.HTTP_200_OK
        data = r.json()
        assert data["target_obj"] == "ZMMR0030"
        assert set(data["calls"]) >= {"EKKO", "MARA"}
        assert "ZMM_MAIN" in data["called_by"]
        assert "ZMMR0030" in data["text"]

    def test_limit_param(self, api_client, dependency_snapshot_data):
        r = api_client.get("/api/dependency-edges/?target_obj=ZMMR0030&limit=1")
        assert r.status_code == status.HTTP_200_OK
        assert len(r.json()["calls"]) <= 1


@pytest.mark.django_db
class TestDependencyGraphView:
    """GET /api/dependency/ (graph)."""

    def test_missing_target(self, api_client):
        r = api_client.get("/api/dependency/")
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    def test_not_found(self, api_client):
        r = api_client.get("/api/dependency/?target_obj=NONEXISTENT999")
        assert r.status_code == status.HTTP_404_NOT_FOUND

    def test_returns_nodes_links(self, api_client, dependency_snapshot_data):
        r = api_client.get("/api/dependency/?target_obj=ZMMR0030")
        assert r.status_code == status.HTTP_200_OK
        data = r.json()
        assert "nodes" in data
        assert "links" in data
        assert "snapshot_time" in data
        assert any(n["id"] == "ZMMR0030" for n in data["nodes"])
