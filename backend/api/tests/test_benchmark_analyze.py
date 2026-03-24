import pytest
from unittest.mock import patch, MagicMock
from api.views.analyze import AnalyzeGuardianView
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

class MockResponse:
    def __init__(self, json_data, status_code=200):
        self.json_data = json_data
        self.status_code = status_code
        self.text = ""

    def json(self):
        return self.json_data

@pytest.fixture
def mock_sap_http_auth():
    with patch("api.sap_client.sap_http_auth", return_value=("user", "pass")):
        with patch("api.sap_client.sap_http_url", return_value="http://mock"):
            with patch("api.sap_client.sap_client", return_value="100"):
                yield

@patch("api.sap_client.requests.get")
@patch("api.views.analyze.fetch_recent_transports_via_http")
def test_benchmark_node_fetch_and_score(mock_fetch_recent, mock_get, benchmark, mock_sap_http_auth):
    # Setup mock data for fetch_recent_transports_via_http
    mock_fetch_recent.return_value = {
        "status": "success",
        "data": [
            {"TRKORR": f"TRK{i}", "objects": [{"OBJECT": "TABL", "OBJ_NAME": f"TABL{i}"}]}
            for i in range(10)
        ]
    }

    # Setup mock requests.get for fetch_object_usage_via_http
    def side_effect(url, **kwargs):
        import time
        # simulate 50ms latency
        time.sleep(0.05)
        return MockResponse({"status": "success", "data": {"usage": "mock"}})
    mock_get.side_effect = side_effect

    view = AnalyzeGuardianView()
    view.selected_trs = [f"TRK{i}" for i in range(10)]
    view.user_id = "test"
    view.progress = {}

    state = {
        "user_input": "", "sap_data_raw": [], "rule_score": 0, "rule_reasons": [],
        "deploy_risk_grade": "Low", "deploy_risk_reason": "", "deploy_risk_actions": [],
        "bc_analysis": "", "fi_analysis": "", "co_analysis": "",
        "mm_analysis": "", "sd_analysis": "", "pp_analysis": "",
        "discussion_history": "", "final_report": "",
        "review_queue": [], "called_counts": {}, "object_usage_data": [],
        "research_context": "", "research_meta": {},
        "graph_context": "", "graph_meta": {},
        "self_rag_meta": {},
        "pipeline_flags": {},
        "pipeline_timings_ms": {},
    }

    def run_node():
        view._node_fetch_and_score(state)

    benchmark(run_node)
