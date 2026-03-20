"""
RAG API: ingest (from DB or custom texts), query (retrieve-only or full RAG).
"""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.config import rag_query_max_k
from api.rag import services


class RAGIngestView(APIView):
    """POST /api/rag/ingest/. Body: { "source": "db"|"texts", "clear": bool, "texts": [...], "max_docs": N }."""

    def post(self, request: Request) -> Response:
        data: dict[str, Any] = getattr(request, "data", None) or {}
        if not isinstance(data, dict):
            data = {}

        clear = data.get("clear", False)
        if clear:
            try:
                chroma_path = Path(services.CHROMA_PERSIST_DIR)
                if chroma_path.is_dir():
                    shutil.rmtree(chroma_path)
            except OSError as e:
                return Response(
                    {"error": f"Clear failed: {e}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        source = data.get("source", "db")
        try:
            if source == "texts":
                texts = data.get("texts") or []
                metadatas = data.get("metadatas")
                if not texts:
                    return Response(
                        {"error": "texts required"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                count = services.ingest_from_texts(texts, metadatas)
            else:
                max_docs = data.get("max_docs")
                if max_docs is not None:
                    try:
                        max_docs = int(max_docs)
                    except (TypeError, ValueError):
                        max_docs = None
                count = services.ingest_from_django_models(max_docs=max_docs)
            return Response(
                {"ok": True, "ingested": count},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            import traceback
            return Response(
                {"error": str(e), "detail": traceback.format_exc()},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class RAGQueryView(APIView):
    """POST /api/rag/query/ with { "query": "...", "k": 5, "retrieve_only": false }."""

    def post(self, request: Request) -> Response:
        query = (
            request.data.get("query") or request.data.get("q") or ""
        ).strip()
        if not query:
            return Response(
                {"error": "query required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        cap = rag_query_max_k()
        try:
            k = min(int(request.data.get("k", 5)), cap)
        except (TypeError, ValueError):
            k = min(5, cap)
        retrieve_only = request.data.get("retrieve_only", False)

        if retrieve_only:
            results = services.retrieve(query, k=k)
            return Response(
                {
                    "query": query,
                    "documents": [
                        {
                            "content": doc.page_content,
                            "metadata": doc.metadata,
                            "score": float(score),
                        }
                        for doc, score in results
                    ],
                },
                status=status.HTTP_200_OK,
            )
        try:
            answer = services.rag_chain_invoke(query, k=k)
            return Response(
                {"query": query, "answer": answer},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
