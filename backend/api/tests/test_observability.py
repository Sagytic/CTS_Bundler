from api.observability import request_id_from

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
