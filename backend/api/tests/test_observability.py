from unittest.mock import patch

from api.observability import _log_llm_tokens, request_id_from


class DummyRequest:
    pass

def test_request_id_from_valid():
    req = DummyRequest()
    req.request_id = "test-123"
    assert request_id_from(req) == "test-123"

def test_request_id_from_none_request():
    assert request_id_from(None) == "-"

def test_request_id_from_missing_attribute():
    req = DummyRequest()
    assert request_id_from(req) == "-"

def test_request_id_from_empty_string():
    req = DummyRequest()
    req.request_id = ""
    assert request_id_from(req) == "-"

def test_request_id_from_none_attribute():
    req = DummyRequest()
    req.request_id = None
    assert request_id_from(req) == "-"


@patch("api.observability.time.perf_counter")
@patch("api.observability.logger")
def test_log_llm_tokens_success(mock_logger, mock_perf_counter):
    mock_perf_counter.return_value = 1.5
    _log_llm_tokens(
        operation="test_op",
        rid="req-123",
        t0=1.0,
        err=None,
        prompt_tokens=10,
        completion_tokens=20,
        total_tokens=30,
    )
    mock_logger.info.assert_called_once_with(
        "llm.%s request_id=%s duration_ms=%.2f ok=%s prompt_tokens=%s completion_tokens=%s total_tokens=%s%s",
        "test_op",
        "req-123",
        500.0,
        True,
        10,
        20,
        30,
        "",
    )


@patch("api.observability.time.perf_counter")
@patch("api.observability.logger")
def test_log_llm_tokens_with_error(mock_logger, mock_perf_counter):
    mock_perf_counter.return_value = 2.0
    _log_llm_tokens(
        operation="test_err",
        rid="req-456",
        t0=1.0,
        err=ValueError("oops"),
        prompt_tokens=5,
        completion_tokens=5,
        total_tokens=10,
    )
    mock_logger.info.assert_called_once_with(
        "llm.%s request_id=%s duration_ms=%.2f ok=%s prompt_tokens=%s completion_tokens=%s total_tokens=%s%s",
        "test_err",
        "req-456",
        1000.0,
        False,
        5,
        5,
        10,
        "",
    )


@patch("api.observability.time.perf_counter")
@patch("api.observability.logger")
def test_log_llm_tokens_with_extra_kwargs(mock_logger, mock_perf_counter):
    mock_perf_counter.return_value = 1.1
    _log_llm_tokens(
        operation="test_extra",
        rid="req-789",
        t0=1.0,
        err=None,
        prompt_tokens=2,
        completion_tokens=3,
        total_tokens=5,
        model="gpt-4",
        temperature=0.7,
    )
    mock_logger.info.assert_called_once_with(
        "llm.%s request_id=%s duration_ms=%.2f ok=%s prompt_tokens=%s completion_tokens=%s total_tokens=%s%s",
        "test_extra",
        "req-789",
        100.00000000000009,
        True,
        2,
        3,
        5,
        " model='gpt-4' temperature=0.7",
    )
