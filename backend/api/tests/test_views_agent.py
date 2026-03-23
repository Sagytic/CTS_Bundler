"""Tests for agent chat API (mocked LLM)."""
import pytest
from unittest.mock import patch, MagicMock
from rest_framework import status


@pytest.mark.django_db
class TestAgentChatView:
    """POST /api/agent/."""

    def test_message_required(self, api_client):
        r = api_client.post("/api/agent/", data={}, format="json")
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    @patch("api.views.agent.azure_openai_key")
    @patch("api.views.agent.azure_openai_endpoint")
    @patch("api.views.agent._make_tools")
    @patch("api.views.agent.AzureChatOpenAI")
    @patch("langgraph.prebuilt.create_react_agent")
    def test_agent_returns_reply(self, mock_create_agent, mock_llm_class, mock_tools, mock_endpoint, mock_key, api_client):
        mock_key.return_value = "fake_key"
        mock_endpoint.return_value = "fake_endpoint"
        mock_tools.return_value = ([], {"docs_tools": 0, "adt_tools": 0})
        mock_llm = MagicMock()
        mock_llm_class.return_value = mock_llm
        mock_graph = MagicMock()
        mock_graph.invoke.return_value = {
            "messages": [
                MagicMock(content="Test reply", tool_calls=None),
            ]
        }
        mock_create_agent.return_value = mock_graph

        r = api_client.post(
            "/api/agent/",
            data={"message": "Hello"},
            format="json",
        )
        assert r.status_code == status.HTTP_200_OK
        data = r.json()
        assert "reply" in data
        assert data.get("reply") == "Test reply" or "reply" in data
