"""Tests for mcp_server tools."""
from unittest.mock import patch

from api.mcp_server import list_transports

@patch("api.mcp_server.fetch_recent_transports_via_http")
def test_list_transports_success(mock_fetch):
    mock_fetch.return_value = {
        "status": "success",
        "data": [
            {"TRKORR": "TR1", "TRFUNCTION": "K", "AS4TEXT": "Main Transport"},
            {"TRKORR": "TR2", "TRFUNCTION": "W", "AS4TEXT": "Customizing Transport"},
            {"TRKORR": "TR3", "TRFUNCTION": "T", "AS4TEXT": "Task"},
            {"TRKORR": "TR4", "trfunction": "k", "as4text": "Lower case function"},
        ]
    }

    result = list_transports("12345")

    mock_fetch.assert_called_once_with(user_id="12345")
    assert "TR 목록:" in result
    assert "- TR1: Main Transport" in result
    assert "- TR2: Customizing Transport" in result
    assert "- TR3: Task" not in result
    assert "- TR4: Lower case function" in result

@patch("api.mcp_server.fetch_recent_transports_via_http")
def test_list_transports_empty(mock_fetch):
    mock_fetch.return_value = {
        "status": "success",
        "data": []
    }

    result = list_transports("12345")
    assert result == "조회된 TR이 없습니다."

@patch("api.mcp_server.fetch_recent_transports_via_http")
def test_list_transports_failure(mock_fetch):
    mock_fetch.return_value = {
        "status": "error",
        "message": "Connection refused"
    }

    result = list_transports("12345")
    assert result == "TR 목록 조회 실패: Connection refused"

@patch("api.mcp_server.fetch_recent_transports_via_http")
def test_list_transports_no_main_transports(mock_fetch):
    mock_fetch.return_value = {
        "status": "success",
        "data": [
            {"TRKORR": "TR3", "TRFUNCTION": "T", "AS4TEXT": "Task"},
            {"TRKORR": "TR4", "TRFUNCTION": "X", "AS4TEXT": "Other"},
        ]
    }

    result = list_transports("12345")
    assert result == "조회된 TR이 없습니다."
