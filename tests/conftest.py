# tests/conftest.py
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if SRC.exists() and str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture()
def sample_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<FlexQueryResponse queryName="TradeVisualTest" type="Trades">
  <Trades>
    <Trade
      accountId="U1234567"
      ibExecID="0000a1"
      symbol="AAPL"
      conid="265598"
      dateTime="2025-01-02;09:31:00 US/Eastern"
      buySell="BUY"
      quantity="10"
      tradePrice="190.12"
      ibCommission="-1.00"
      exchange="NASDAQ"
      orderType="LMT"
      orderTime="2025-01-02;09:30:55 US/Eastern"
    />
    <Trade
      accountId="U1234567"
      ibExecID="0000a2"
      symbol="AAPL"
      conid="265598"
      dateTime="2025-01-02;15:59:30 US/Eastern"
      buySell="SELL"
      quantity="5"
      tradePrice="191.05"
      ibCommission="-0.60"
      exchange="NASDAQ"
      orderType="MKT"
      orderTime="2025-01-02;15:59:25 US/Eastern"
    />
  </Trades>
</FlexQueryResponse>
"""


@pytest.fixture()
def parsed_executions(sample_xml):
    from src.io.ibkr_flex_parser import IBKRFlexParser
    return IBKRFlexParser.parse_xml(sample_xml)


@pytest.fixture()
def session():
    # In-memory DB session for reconstructor tests.
    from sqlmodel import SQLModel, Session, create_engine
    from sqlalchemy.pool import StaticPool

    # Import models so tables are registered on SQLModel.metadata.
    import src.db.models  # noqa: F401

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    with Session(engine) as s:
        yield s
