# tests/conftest.py
"""Test configuration and fixtures (aligned with current README)."""

import pytest
from datetime import datetime, timezone, date

from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from src.db.models import Trade, TradeDay


@pytest.fixture(name="engine")
def engine_fixture():
    # In-memory SQLite that persists across the test session connection pool.
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture(name="session")
def session_fixture(engine):
    with Session(engine) as session:
        yield session


@pytest.fixture(name="account_id")
def account_id_fixture():
    return "TEST_ACCOUNT"


@pytest.fixture(name="sample_xml")
def sample_xml_fixture():
    # Minimal IBKR Flex XML with 2 trades
    return """<?xml version="1.0" encoding="UTF-8"?>
<FlexQueryResponse queryName="Trade Summary">
  <FlexStatements>
    <FlexStatement accountId="U12345678" fromDate="2025-01-01" toDate="2025-01-31">
      <Trades>
        <Trade accountId="U12345678" assetCategory="STOCKS" currency="USD" conid="265598" symbol="AAPL"
               buySell="BUY" tradeID="123001" tradeTime="2025-01-15 09:30:00"
               quantity="100" tradePrice="150.25" ibCommission="-10.00"
               exchange="SMART" orderType="LMT"></Trade>
        <Trade accountId="U12345678" assetCategory="STOCKS" currency="USD" conid="265598" symbol="AAPL"
               buySell="SELL" tradeID="123002" tradeTime="2025-01-20 14:15:00"
               quantity="50" tradePrice="151.80" ibCommission="-5.00"
               exchange="SMART" orderType="LMT"></Trade>
      </Trades>
    </FlexStatement>
  </FlexStatements>
</FlexQueryResponse>
"""


@pytest.fixture(name="sample_trade_days")
def sample_trade_days_fixture(session: Session, account_id: str):
    # Create one closed trade with two TradeDay rows so MetricsCalculator can be smoke-tested.
    t = Trade(
        account_id=account_id,
        symbol="AAPL",
        direction="LONG",
        status="closed",
        opened_at_utc=datetime(2025, 1, 15, 14, 30, tzinfo=timezone.utc),
        closed_at_utc=datetime(2025, 1, 20, 19, 15, tzinfo=timezone.utc),
        quantity_opened=100,
        gross_pnl_total=100.0,
        commission_total=15.0,
        net_pnl_total=85.0,
    )
    session.add(t)
    session.commit()
    session.refresh(t)

    td1 = TradeDay(
        trade_id=t.id,
        day_date_local=date(2025, 1, 15),
        realized_gross=0.0,
        commissions=10.0,
        realized_net=-10.0,
        shares_closed=0.0,
    )
    td2 = TradeDay(
        trade_id=t.id,
        day_date_local=date(2025, 1, 20),
        realized_gross=100.0,
        commissions=5.0,
        realized_net=95.0,
        shares_closed=50.0,
    )

    session.add(td1)
    session.add(td2)
    session.commit()

    return t
