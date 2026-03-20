"""agent_reply_cleanup dedupe / strip tests."""
from __future__ import annotations

from api.agent_reply_cleanup import clean_agent_reply_text


def test_strip_legacy_hint_and_dedupe_tr_heading():
    raw = """아래는 list_transports 조회 결과입니다. 안내 문구.

- EDAK901412: A
- EDAK901372: B

티켓 정보

### TR 목록
- EDAK901412: A
- EDAK901372: B

다음 단계
"""
    out = clean_agent_reply_text(raw)
    assert "list_transports 조회 결과" not in out
    assert out.count("EDAK901412") == 1
    assert "### TR 목록" in out


def test_normalize_glued_heading():
    raw = "없음### TR 목록\n- EDAK901412: x\n"
    out = clean_agent_reply_text(raw)
    assert "없음###" not in out
    assert "\n\n### TR 목록" in out


def test_strip_leading_docs_search_json_blob():
    blob = (
        '{"results":[{"id":"/x","title":"T1","url":"https://help.sap.com/a.html",'
        '"snippet":"s","score":0.1,"metadata":{}}]}'
    )
    tail = "ABAP 7.52에서 WHERE는 조건을 지정합니다."
    raw = blob + tail
    out = clean_agent_reply_text(raw)
    assert "results" not in out
    assert '"id"' not in out
    assert tail in out
