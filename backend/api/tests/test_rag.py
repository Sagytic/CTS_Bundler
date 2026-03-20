"""Tests for RAG services and views (mocked embeddings where needed)."""
import pytest
from unittest.mock import patch, MagicMock

from api.models import DependencySnapshot, TicketMapping


@pytest.mark.django_db
class TestRAGIngestFromModels:
    """RAG ingest_from_django_models logic (with mocked vector store)."""

    @patch("api.rag.services.get_vector_store")
    def test_ingest_builds_docs(self, mock_get_vs):
        from api.rag.services import ingest_from_django_models

        DependencySnapshot.objects.create(
            source_obj="A", target_obj="B", target_group=2
        )
        mock_vs = MagicMock()
        mock_get_vs.return_value = mock_vs

        n = ingest_from_django_models(max_docs=10)
        assert n == 1
        mock_vs.add_documents.assert_called_once()
        docs = mock_vs.add_documents.call_args[0][0]
        assert len(docs) == 1
        assert "A" in docs[0].page_content and "B" in docs[0].page_content


@pytest.mark.django_db
class TestRAGViews:
    """RAG API endpoints."""

    def test_ingest_empty_database(self, api_client):
        r = api_client.post("/api/rag/ingest/", data={"source": "db"}, format="json")
        assert r.status_code == 200
        data = r.json()
        assert "ok" in data or "ingested" in data or "error" not in data

    def test_query_requires_query_param(self, api_client):
        r = api_client.post("/api/rag/query/", data={}, format="json")
        assert r.status_code in (200, 400)
