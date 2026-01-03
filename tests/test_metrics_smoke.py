# tests/test_parser.py
"""Parser + timestamp smoke tests."""

from src.io.ibkr_flex_parser import IBKRFlexParser


def test_parse_valid_xml(sample_xml):
    executions = IBKRFlexParser.parse_xml(sample_xml)
    assert len(executions) == 2
    assert executions[0].symbol == "AAPL"
    assert executions[0].side in ("BUY", "SELL")


def test_parse_timestamp():
    ts_str = "2025-01-15 09:30:00"
    dt_et, dt_utc = IBKRFlexParser.parse_timestamp(ts_str)

    assert dt_et.year == 2025
    assert dt_et.month == 1
    assert dt_et.day == 15
    assert dt_utc.tzname() == "UTC"
