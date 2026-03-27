"""sap_client helpers."""

from unittest.mock import patch

import requests

from api.sap_client import fetch_dependency_graph_via_http, filter_main_transports


def test_filter_main_transports_keeps_k_and_w_only():
    rows = [
        {"TRKORR": "N1", "TRFUNCTION": "K", "AS4TEXT": "main"},
        {"TRKORR": "N2", "trfunction": "w", "AS4TEXT": "cust"},
        {"TRKORR": "T1", "TRFUNCTION": "T", "AS4TEXT": "task"},
        {"TRKORR": "N3", "TRFUNCTION": "", "AS4TEXT": "empty"},
    ]
    out = filter_main_transports(rows)
    assert [r["TRKORR"] for r in out] == ["N1", "N2"]


@patch("api.sap_client.sap_http_url")
@patch("api.sap_client.sap_http_auth")
@patch("api.sap_client.sap_client")
@patch("api.sap_client.requests.get")
def test_fetch_dependency_graph_success(mock_get, mock_client, mock_auth, mock_url):
    mock_url.return_value = "http://sap.example.com"
    mock_auth.return_value = ("user", "pass")
    mock_client.return_value = "100"

    mock_response = mock_get.return_value
    mock_response.status_code = 200
    mock_response.json.return_value = {"nodes": [], "edges": []}

    result = fetch_dependency_graph_via_http(target_obj="OBJ1")

    assert result["status"] == "success"
    assert result["data"] == {"nodes": [], "edges": []}
    mock_get.assert_called_once()
    args, kwargs = mock_get.call_args
    assert args[0] == "http://sap.example.com"
    assert kwargs["params"] == {"sap-client": "100", "action": "dependency", "target_obj": "OBJ1"}
    assert kwargs["auth"] == requests.auth.HTTPBasicAuth("user", "pass")


@patch("api.sap_client.sap_http_url")
@patch("api.sap_client.sap_http_auth")
@patch("api.sap_client.sap_client")
def test_fetch_dependency_graph_missing_config(mock_client, mock_auth, mock_url):
    # Test missing URL
    mock_url.return_value = ""
    mock_auth.return_value = ("user", "pass")
    mock_client.return_value = "100"

    result = fetch_dependency_graph_via_http()
    assert result["status"] == "error"
    assert "not configured" in result["message"]

    # Test missing Auth
    mock_url.return_value = "http://sap.example.com"
    mock_auth.return_value = ("", "")

    result = fetch_dependency_graph_via_http()
    assert result["status"] == "error"
    assert "not configured" in result["message"]


@patch("api.sap_client.sap_http_url")
@patch("api.sap_client.sap_http_auth")
@patch("api.sap_client.sap_client")
@patch("api.sap_client.requests.get")
def test_fetch_dependency_graph_http_error(mock_get, mock_client, mock_auth, mock_url):
    mock_url.return_value = "http://sap.example.com"
    mock_auth.return_value = ("user", "pass")
    mock_client.return_value = "100"

    mock_response = mock_get.return_value
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"

    result = fetch_dependency_graph_via_http()

    assert result["status"] == "error"
    assert "HTTP 500" in result["message"]
    assert "Internal Server Error" in result["message"]


@patch("api.sap_client.sap_http_url")
@patch("api.sap_client.sap_http_auth")
@patch("api.sap_client.sap_client")
@patch("api.sap_client.requests.get")
def test_fetch_dependency_graph_request_exception(mock_get, mock_client, mock_auth, mock_url):
    mock_url.return_value = "http://sap.example.com"
    mock_auth.return_value = ("user", "pass")
    mock_client.return_value = "100"

    mock_get.side_effect = requests.exceptions.RequestException("Connection Timeout")

    result = fetch_dependency_graph_via_http()

    assert result["status"] == "error"
    assert "SAP 서버 통신 중 오류가 발생했습니다" in result["message"]
