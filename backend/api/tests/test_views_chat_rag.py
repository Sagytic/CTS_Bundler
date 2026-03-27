import pytest
from unittest.mock import patch, MagicMock

from rest_framework.test import APIClient
from django.urls import reverse

import hashlib
import time

@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
class TestSAPChatRAGView:
    def test_chat_rag_missing_message(self, api_client):
        url = reverse("chat-rag")
        response = api_client.post(url, data={}, format="json")
        assert response.status_code == 400
        assert response.json() == {"error": "message required"}

        response2 = api_client.post(url, data={"message": "   "}, format="json")
        assert response2.status_code == 400
        assert response2.json() == {"error": "message required"}

    @patch("api.views.chat_rag.azure_openai_key")
    @patch("api.views.chat_rag.azure_openai_endpoint")
    def test_chat_rag_missing_config(self, mock_endpoint, mock_key, api_client):
        mock_key.return_value = ""
        mock_endpoint.return_value = "https://example.com"

        url = reverse("chat-rag")
        response = api_client.post(url, data={"message": "Hello"}, format="json")
        assert response.status_code == 503
        assert response.json() == {"error": "Azure OpenAI not configured"}

    @patch("api.views.chat_rag.azure_openai_key")
    @patch("api.views.chat_rag.azure_openai_endpoint")
    @patch("api.views.chat_rag.chat_rag_cache_ttl_sec")
    def test_chat_rag_cache_hit(self, mock_ttl, mock_endpoint, mock_key, api_client):
        mock_key.return_value = "key"
        mock_endpoint.return_value = "endpoint"
        mock_ttl.return_value = 3600

        user_input = "Hello"
        cache_key = hashlib.sha256(user_input.encode()).hexdigest()

        from api.views.chat_rag import _CHAT_CACHE
        _CHAT_CACHE[cache_key] = ("Cached response", time.time())

        url = reverse("chat-rag")
        response = api_client.post(url, data={"message": user_input, "use_cache": True}, format="json")

        assert response.status_code == 200
        assert response.json() == {"reply": "Cached response", "cached": True}

        # Cleanup
        del _CHAT_CACHE[cache_key]

    @patch("api.views.chat_rag.azure_openai_key")
    @patch("api.views.chat_rag.azure_openai_endpoint")
    @patch("api.views.chat_rag.azure_openai_fast_deployment")
    @patch("api.views.chat_rag.azure_openai_api_version")
    @patch("api.views.chat_rag.chat_rag_cache_ttl_sec")
    @patch("api.views.chat_rag.ChatPromptTemplate")
    @patch("api.views.chat_rag.AzureChatOpenAI")
    def test_chat_rag_standard(self, mock_llm_class, mock_prompt_class, mock_ttl, mock_api_version, mock_deployment, mock_endpoint, mock_key, api_client):
        mock_key.return_value = "key"
        mock_endpoint.return_value = "endpoint"
        mock_deployment.return_value = "deployment"
        mock_api_version.return_value = "2023-05-15"
        mock_ttl.return_value = 0  # Disable cache

        mock_llm_instance = MagicMock()
        mock_llm_class.return_value = mock_llm_instance

        mock_prompt_instance = MagicMock()
        mock_prompt_class.from_messages.return_value = mock_prompt_instance

        # Mock the chain invocation
        mock_chain = MagicMock()
        mock_prompt_instance.__or__.return_value = mock_chain

        mock_result = MagicMock()
        mock_result.content = "Standard AI Reply"
        mock_chain.invoke.return_value = mock_result

        url = reverse("chat-rag")
        response = api_client.post(url, data={"message": "Hello"}, format="json")

        assert response.status_code == 200
        assert response.json() == {"reply": "Standard AI Reply", "cached": False}
        mock_chain.invoke.assert_called_once_with({"input": "Hello", "context": ""})

    @patch("api.views.chat_rag.azure_openai_key")
    @patch("api.views.chat_rag.azure_openai_endpoint")
    @patch("api.views.chat_rag.azure_openai_fast_deployment")
    @patch("api.views.chat_rag.azure_openai_api_version")
    @patch("api.views.chat_rag.chat_rag_cache_ttl_sec")
    @patch("api.views.chat_rag.ChatPromptTemplate")
    @patch("api.views.chat_rag.AzureChatOpenAI")
    @patch("api.rag.services.retrieve")
    def test_chat_rag_with_rag(self, mock_retrieve, mock_llm_class, mock_prompt_class, mock_ttl, mock_api_version, mock_deployment, mock_endpoint, mock_key, api_client):
        mock_key.return_value = "key"
        mock_endpoint.return_value = "endpoint"
        mock_deployment.return_value = "deployment"
        mock_api_version.return_value = "2023-05-15"
        mock_ttl.return_value = 0  # Disable cache

        # Mock retrieval results
        mock_doc = MagicMock()
        mock_doc.page_content = "RAG context document"
        mock_retrieve.return_value = [(mock_doc, 0.9)]

        mock_llm_instance = MagicMock()
        mock_llm_class.return_value = mock_llm_instance

        mock_prompt_instance = MagicMock()
        mock_prompt_class.from_messages.return_value = mock_prompt_instance

        # Mock the chain invocation
        mock_chain = MagicMock()
        mock_prompt_instance.__or__.return_value = mock_chain

        mock_result = MagicMock()
        mock_result.content = "RAG AI Reply"
        mock_chain.invoke.return_value = mock_result

        url = reverse("chat-rag")
        response = api_client.post(url, data={"message": "Hello", "use_rag": True}, format="json")

        assert response.status_code == 200
        assert response.json() == {"reply": "RAG AI Reply", "cached": False}

        mock_retrieve.assert_called_once()
        expected_context = "\n\n[참고 문서]\n" + "RAG context document"
        mock_chain.invoke.assert_called_once_with({"input": "Hello", "context": expected_context})

    @patch("api.views.chat_rag.azure_openai_key")
    @patch("api.views.chat_rag.azure_openai_endpoint")
    @patch("api.views.chat_rag.azure_openai_fast_deployment")
    @patch("api.views.chat_rag.azure_openai_api_version")
    @patch("api.views.chat_rag.chat_rag_cache_ttl_sec")
    @patch("api.views.chat_rag.ChatPromptTemplate")
    @patch("api.views.chat_rag.AzureChatOpenAI")
    def test_chat_rag_structured(self, mock_llm_class, mock_prompt_class, mock_ttl, mock_api_version, mock_deployment, mock_endpoint, mock_key, api_client):
        mock_key.return_value = "key"
        mock_endpoint.return_value = "endpoint"
        mock_deployment.return_value = "deployment"
        mock_api_version.return_value = "2023-05-15"
        mock_ttl.return_value = 0  # Disable cache

        mock_llm_instance = MagicMock()
        mock_llm_class.return_value = mock_llm_instance

        mock_structured_llm = MagicMock()
        mock_llm_instance.with_structured_output.return_value = mock_structured_llm

        mock_prompt_instance = MagicMock()
        mock_prompt_class.from_messages.return_value = mock_prompt_instance

        # Mock the chain invocation
        mock_chain = MagicMock()
        mock_prompt_instance.__or__.return_value = mock_chain

        mock_result = MagicMock()
        mock_result.reply = "Structured Reply"
        mock_result.intent = "general"
        mock_result.suggested_actions = ["action1"]
        mock_chain.invoke.return_value = mock_result

        url = reverse("chat-rag")
        response = api_client.post(url, data={"message": "Hello", "use_structured": True}, format="json")

        assert response.status_code == 200
        assert response.json() == {
            "reply": "Structured Reply",
            "intent": "general",
            "suggested_actions": ["action1"],
            "cached": False
        }

        mock_llm_instance.with_structured_output.assert_called_once()
        mock_chain.invoke.assert_called_once_with({"input": "Hello", "context": ""})

    @patch("api.views.chat_rag.azure_openai_key")
    @patch("api.views.chat_rag.azure_openai_endpoint")
    @patch("api.views.chat_rag.azure_openai_fast_deployment")
    @patch("api.views.chat_rag.azure_openai_api_version")
    @patch("api.views.chat_rag.chat_rag_cache_ttl_sec")
    @patch("api.views.chat_rag.ChatPromptTemplate")
    @patch("api.views.chat_rag.AzureChatOpenAI")
    def test_chat_rag_exception(self, mock_llm_class, mock_prompt_class, mock_ttl, mock_api_version, mock_deployment, mock_endpoint, mock_key, api_client):
        mock_key.return_value = "key"
        mock_endpoint.return_value = "endpoint"
        mock_deployment.return_value = "deployment"
        mock_api_version.return_value = "2023-05-15"
        mock_ttl.return_value = 0  # Disable cache

        mock_llm_instance = MagicMock()
        mock_llm_class.return_value = mock_llm_instance

        mock_prompt_instance = MagicMock()
        mock_prompt_class.from_messages.return_value = mock_prompt_instance

        # Mock the chain invocation
        mock_chain = MagicMock()
        mock_prompt_instance.__or__.return_value = mock_chain

        mock_chain.invoke.side_effect = Exception("LLM failure")

        url = reverse("chat-rag")
        response = api_client.post(url, data={"message": "Hello"}, format="json")

        assert response.status_code == 200
        assert response.json() == {
            "reply": "챗봇 응답 중 오류가 발생했습니다. 상세 내용은 시스템 로그를 확인해 주세요.",
            "cached": False
        }
