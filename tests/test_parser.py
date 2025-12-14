# tests/test_parser.py
"""Test IBKR XML parser."""

from src.io.ibkr_flex_parser import IBKRFlexParser


def test_parse_valid_xml(sample_xml):
    """Test parsing valid IBKR XML."""
    executions = IBKRFlexParser.parse_xml(sample_xml)
    
    assert len(executions) == 2
    assert executions[0].symbol == "AAPL"
    assert executions[0].side == "BUY"
    assert executions[0].quantity == 100
    assert executions[0].price == 150.25
    assert executions[1].side == "SELL"


def test_parse_timestamp():
    """Test timestamp parsing."""
    ts_str = "2025-01-15 09:30:00"
    dt_et, dt_utc = IBKRFlexParser.parse_timestamp(ts_str)
    
    assert dt_et.year == 2025
    assert dt_et.month == 1
    assert dt_et.day == 15
    assert dt_utc.tzname() == 'UTC'


def test_idempotent_import(session, test_account, sample_xml):
    """Test that re-importing same XML doesn't create duplicates."""
    from src.io.importer import IBKRImporter
    
    executions = IBKRFlexParser.parse_xml(sample_xml)
    
    # First import
    total1, new1, _ = IBKRImporter.import_executions(
        session=session,
        account=test_account,
        parsed_executions=executions,
    )
    
    # Second import (same data)
    total2, new2, warnings = IBKRImporter.import_executions(
        session=session,
        account=test_account,
        parsed_executions=executions,
    )
    
    assert total1 == 2 and new1 == 2
    assert total2 == 2 and new2 == 0  # No new executions
    assert len(warnings) == 2  # Duplicates logged as warnings
