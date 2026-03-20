"""sap_client helpers."""

from api.sap_client import filter_main_transports


def test_filter_main_transports_keeps_k_and_w_only():
    rows = [
        {"TRKORR": "N1", "TRFUNCTION": "K", "AS4TEXT": "main"},
        {"TRKORR": "N2", "trfunction": "w", "AS4TEXT": "cust"},
        {"TRKORR": "T1", "TRFUNCTION": "T", "AS4TEXT": "task"},
        {"TRKORR": "N3", "TRFUNCTION": "", "AS4TEXT": "empty"},
    ]
    out = filter_main_transports(rows)
    assert [r["TRKORR"] for r in out] == ["N1", "N2"]
