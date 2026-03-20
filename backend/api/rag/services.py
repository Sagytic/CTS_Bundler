"""
RAG service: embeddings, vector store (ChromaDB), ingest, retrieve & generate.
Uses Azure OpenAI Embeddings; config via api.config.
"""
from __future__ import annotations

from pathlib import Path

from api.config import (
    azure_openai_api_version,
    azure_openai_embedding_deployment,
    azure_openai_endpoint,
    azure_openai_key,
    azure_openai_fast_deployment,
    env,
    llm_rag_chain_temperature,
    rag_default_k,
)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
CHROMA_PERSIST_DIR = env("CHROMA_PERSIST_DIR", str(BASE_DIR / "data" / "chroma"))
RAG_COLLECTION_NAME = env("RAG_COLLECTION_NAME", "cts_bundler_kb")


def get_embeddings():
    """Azure OpenAI Embeddings. Fallback to OpenAI-compatible if Azure not set."""
    if azure_openai_endpoint() and azure_openai_key():
        from langchain_openai import AzureOpenAIEmbeddings
        return AzureOpenAIEmbeddings(
            azure_deployment=azure_openai_embedding_deployment(),
            api_version=azure_openai_api_version(),
            azure_endpoint=azure_openai_endpoint(),
            api_key=azure_openai_key(),
        )
    from langchain_openai import OpenAIEmbeddings
    return OpenAIEmbeddings(
        model=env("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
        api_key=env("OPENAI_API_KEY") or env("AZURE_OPENAI_API_KEY"),
    )


def get_vector_store():
    """ChromaDB persistent vector store with project-specific collection."""
    from langchain_chroma import Chroma
    Path(CHROMA_PERSIST_DIR).mkdir(parents=True, exist_ok=True)
    return Chroma(
        collection_name=RAG_COLLECTION_NAME,
        embedding_function=get_embeddings(),
        persist_directory=CHROMA_PERSIST_DIR,
    )


def ingest_from_django_models(max_docs=None):
    """Build RAG documents from Django DependencySnapshot and TicketMapping.
    max_docs: 최대 문서 수 (None이면 RAG_INGEST_MAX_DOCS 또는 3000).
    """
    import django
    if not django.apps.apps.ready:
        django.setup()
    from api.config import env_int
    from api.models import DependencySnapshot, TicketMapping
    from langchain_core.documents import Document

    cap = max_docs if max_docs is not None else env_int("RAG_INGEST_MAX_DOCS", 3000)
    docs = []
    # DependencySnapshot: "source_obj calls target_obj (group N)"
    for row in DependencySnapshot.objects.all()[:cap]:
        docs.append(Document(
            page_content=f"SAP 오브젝트 종속성: {row.source_obj} → {row.target_obj} (유형: {row.target_group})",
            metadata={"source": "dependency", "source_obj": row.source_obj, "target_obj": row.target_obj},
        ))
    remaining = cap - len(docs)
    # TicketMapping (남은 cap만큼만)
    if remaining > 0:
        for row in TicketMapping.objects.all()[:remaining]:
            docs.append(Document(
                page_content=f"TR/오브젝트 매핑: {row.target_key} | 티켓: {row.ticket_id} | 요구사항: {row.description}",
                metadata={"source": "ticket", "target_key": row.target_key, "ticket_id": row.ticket_id},
            ))
    if not docs:
        return 0
    vs = get_vector_store()
    vs.add_documents(docs)
    return len(docs)


def ingest_from_texts(texts, metadatas=None):
    """Ingest custom text chunks (e.g. from uploaded docs or ABAP guidelines)."""
    from langchain_core.documents import Document
    if metadatas is None:
        metadatas = [{}] * len(texts)
    docs = [Document(page_content=t, metadata=m) for t, m in zip(texts, metadatas)]
    if not docs:
        return 0
    get_vector_store().add_documents(docs)
    return len(docs)


def retrieve(query: str, k: int | None = None):
    """Semantic search; returns list of (Document, score)."""
    kk = k if k is not None else rag_default_k()
    vs = get_vector_store()
    results = vs.similarity_search_with_relevance_scores(query, k=kk)
    return results


def rag_chain_invoke(query: str, k: int | None = None, llm=None):
    """Full RAG: retrieve context + generate answer with LLM."""
    from api.prompts.rag_chain import RAG_CHAIN_HUMAN, RAG_CHAIN_SYSTEM
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_openai import AzureChatOpenAI

    kk = k if k is not None else rag_default_k()
    retrieved = retrieve(query, k=kk)
    if not retrieved:
        context = "관련 문서가 없습니다."
    else:
        context = "\n\n".join([doc.page_content for doc, _ in retrieved])

    if llm is None:
        llm = AzureChatOpenAI(
            azure_deployment=azure_openai_fast_deployment(),
            api_version=azure_openai_api_version(),
            azure_endpoint=azure_openai_endpoint(),
            api_key=azure_openai_key(),
            temperature=llm_rag_chain_temperature(),
        )
    prompt = ChatPromptTemplate.from_messages([
        ("system", RAG_CHAIN_SYSTEM),
        ("human", RAG_CHAIN_HUMAN),
    ])
    chain = prompt | llm
    from api.observability import track_llm_request

    with track_llm_request("rag_chain", request_id="-"):
        return chain.invoke({"context": context, "query": query}).content
