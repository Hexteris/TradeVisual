# tests/conftest.py
"""Test configuration and fixtures."""

import pytest
import os
from sqlmodel import Session, create_engine, SQLModel
from sqlmodel.pool import StaticPool

from src.db.models import User, Account, Execution, Trade, TradeDay
from src.io.ibkr_flex_parser import IBKRFlexParser
from src.auth import AuthManager


@pytest.fixture(name="session")
def session_fixture():
    """Create in-memory SQLite test database."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="test_user")
def test_user_fixture(session: Session):
    """Create test user."""
    hashed_pw = AuthManager.hash_password("testpass123")
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=hashed_pw,
    )
    session.add(user)
    session.commit()
    return user


@pytest.fixture(name="test_account")
def test_account_fixture(session: Session, test_user: User):
    """Create test account."""
    account = Account(
        user_id=test_user.id,
        account_number="U12345678",
        currency="USD",
    )
    session.add(account)
    session.commit()
    return account


@pytest.fixture(name="sample_xml")
def sample_xml_fixture():
    """Provide sample IBKR XML."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<FlexQueryResponse queryName="Trade Summary">
    <FlexStatements>
        <FlexStatement accountId="U12345678" fromDate="2025-01-01" toDate="2025-01-31">
            <Trades>
                <Trade accountId="U12345678" assetCategory="STOCKS" currency="USD" conid="265598" symbol="AAPL" 
                       buySell="BUY" tradeID="123001" tradeTime="2025-01-15 09:30:00"
                       quantity="100" tradePrice="150.25" ibCommission="-10.00"
                       exchange="SMART" orderType="LMT">
                </Trade>
                <Trade accountId="U12345678" assetCategory="STOCKS" currency="USD" conid="265598" symbol="AAPL" 
                       buySell="SELL" tradeID="123002" tradeTime="2025-01-20 14:15:00"
                       quantity="50" tradePrice="151.80" ibCommission="-5.00"
                       exchange="SMART" orderType="LMT">
                </Trade>
            </Trades>
        </FlexStatement>
    </FlexStatements>
</FlexQueryResponse>
"""
