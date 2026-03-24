"""
Chat with optional RAG: retrieved context + optional structured output + response cache.
"""
from __future__ import annotations

import hashlib
import logging
import time
from typing import Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import AzureChatOpenAI
from pydantic import BaseModel, Field
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.config import (
    azure_openai_api_version,
    azure_openai_endpoint,
    azure_openai_fast_deployment,
    azure_openai_key,
    chat_rag_cache_ttl_sec,
    llm_chat_rag_temperature,
    rag_default_k,
)
from api.observability import track_llm_request
from api.prompts.chat_rag import RAG_CHAT_SYSTEM_PROMPT, rag_chat_system_with_context_hint

_logger = logging.getLogger("cts.ai")
_CHAT_CACHE: dict[str, tuple[str, float]] = {}


class ChatStructuredOutput(BaseModel):
    """Structured reply for use_structured=True."""

    reply: str = Field(description="전체 답변 본문 (마크다운)")
    intent: str = Field(
        description="질문 의도 요약: general|abap_code|tcode|table|transport|dependency|other"
    )
    suggested_actions: list[str] = Field(
        default_factory=list, description="추천 후속 액션 0~3개"
    )


class SAPChatRAGView(APIView):
    """
    POST /api/chat/rag/ with message, use_rag, use_structured, use_cache.

    **구조화 출력** (`use_structured: true`): Pydantic 스키마(reply, intent, suggested_actions).
    **비구조화** (기본): 자유 텍스트 reply만. RAG는 `use_rag`로 켜면 retrieve 후 system에 문서 우선 지시를 덧붙임.
    """

    def post(self, request: Request) -> Response:
        user_input = (
            request.data.get("message") or request.data.get("input") or ""
        ).strip()
        use_rag = request.data.get("use_rag", False)
        use_structured = request.data.get("use_structured", False)
        use_cache = request.data.get("use_cache", True)

        if not user_input:
            return Response(
                {"error": "message required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not azure_openai_key() or not azure_openai_endpoint():
            return Response(
                {"error": "Azure OpenAI not configured"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        ttl = chat_rag_cache_ttl_sec()
        cache_key: Optional[str] = None
        if use_cache and ttl > 0:
            cache_key = hashlib.sha256(user_input.encode()).hexdigest()
            if cache_key in _CHAT_CACHE:
                reply, ts = _CHAT_CACHE[cache_key]
                if time.time() - ts < ttl:
                    return Response(
                        {"reply": reply, "cached": True},
                        status=status.HTTP_200_OK,
                    )

        llm = AzureChatOpenAI(
            azure_deployment=azure_openai_fast_deployment(),
            api_version=azure_openai_api_version(),
            azure_endpoint=azure_openai_endpoint(),
            api_key=azure_openai_key(),
            temperature=llm_chat_rag_temperature(),
        )

        context = ""
        if use_rag:
            try:
                from api.rag import services
                results = services.retrieve(user_input, k=rag_default_k())
                if results:
                    context = "\n\n[참고 문서]\n" + "\n\n".join(
                        d.page_content for d, _ in results
                    )
            except Exception:
                context = ""

        system = (
            rag_chat_system_with_context_hint(RAG_CHAT_SYSTEM_PROMPT)
            if context
            else RAG_CHAT_SYSTEM_PROMPT
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system", system),
            ("human", "{context}\n\n[질문]\n{input}"),
        ])

        try:
            if use_structured:
                structured_llm = llm.with_structured_output(ChatStructuredOutput)
                chain = prompt | structured_llm
                with track_llm_request(
                    "chat_rag_structured",
                    request=request,
                    use_rag=use_rag,
                    deployment=azure_openai_fast_deployment(),
                ):
                    out = chain.invoke({"input": user_input, "context": context})
                reply = out.reply
                if use_cache and cache_key and ttl > 0:
                    _CHAT_CACHE[cache_key] = (reply, time.time())
                return Response(
                    {
                        "reply": reply,
                        "intent": out.intent,
                        "suggested_actions": out.suggested_actions,
                        "cached": False,
                    },
                    status=status.HTTP_200_OK,
                )
            chain = prompt | llm
            with track_llm_request(
                "chat_rag",
                request=request,
                use_rag=use_rag,
                deployment=azure_openai_fast_deployment(),
            ):
                result = chain.invoke({"input": user_input, "context": context})
            reply = result.content if hasattr(result, "content") else str(result)
        except Exception as e:
            _logger.exception("Chat RAG error: %s", e)
            reply = "챗봇 응답 중 오류가 발생했습니다. 상세 내용은 시스템 로그를 확인해 주세요."

        if use_cache and cache_key and ttl > 0:
            _CHAT_CACHE[cache_key] = (reply, time.time())
        return Response(
            {"reply": reply, "cached": False},
            status=status.HTTP_200_OK,
        )
