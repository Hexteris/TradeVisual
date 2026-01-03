# tests/test_parser.py
from __future__ import annotations

import pytz


def test_parse_xml_smoke(parsed_executions):
    assert len(parsed_executions) == 2

    e0 = parsed_executions[0]
    assert e0.account_id == "U1234567"
    assert e0.ib_execution_id == "0000a1"
    assert e0.symbol == "AAPL"
    assert e0.conid == 265598
    assert e0.ts_raw.startswith("2025-01-02;09:31:00")
    assert e0.side == "BUY"
    assert e0.quantity == 10.0
    assert e0.price == 190.12
    assert e0.commission == -1.0
    assert e0.exchange == "NASDAQ"
    assert e0.order_type == "LMT"
    assert e0.order_time_utc is not None
    assert e0.ts_utc.tzinfo is not None
    assert e0.ts_utc.tzinfo == pytz.UTC

    e1 = parsed_executions[1]
    assert e1.ib_execution_id == "0000a2"
    assert e1.side == "SELL"
    assert e1.quantity == 5.0
