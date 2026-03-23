"""Simple SAP chat: single LLM call, no RAG."""
from __future__ import annotations

import logging

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from api.config import (
    azure_openai_api_version,
    azure_openai_endpoint,
    azure_openai_fast_deployment,
    azure_openai_key,
    llm_simple_chat_temperature,
)
from api.observability import track_llm_request
from api.prompts.simple_chat import SIMPLE_CHAT_SYSTEM_PROMPT
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import AzureChatOpenAI

_logger = logging.getLogger("cts.ai")


class SAPChatView(APIView):
    """POST /api/chat/ with {"message": "..."}. Returns {"reply": "..."}."""

    def post(self, request: Request) -> Response:
        user_input = (request.data.get("message") or "").strip()
        if not user_input:
            return Response(
                {"error": "message is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not azure_openai_key() or not azure_openai_endpoint():
            return Response(
                {"error": "Azure OpenAI not configured"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        llm = AzureChatOpenAI(
            azure_deployment=azure_openai_fast_deployment(),
            api_version=azure_openai_api_version(),
            azure_endpoint=azure_openai_endpoint(),
            api_key=azure_openai_key(),
            temperature=llm_simple_chat_temperature(),
        )
        prompt = ChatPromptTemplate.from_messages([
            ("system", SIMPLE_CHAT_SYSTEM_PROMPT),
            ("human", "{input}"),
        ])
        chain = prompt | llm

        try:
            with track_llm_request(
                "simple_chat",
                request=request,
                deployment=azure_openai_fast_deployment(),
            ):
                result = chain.invoke({"input": user_input})
            reply = result.content if hasattr(result, "content") else str(result)
        except Exception as e:
            _logger.exception("Simple chat error: %s", e)
            reply = "챗봇 응답 중 오류가 발생했습니다. 상세 내용은 서버 로그를 확인하세요."

        return Response({"reply": reply}, status=status.HTTP_200_OK)
