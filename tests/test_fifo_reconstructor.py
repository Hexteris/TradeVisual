# tests/test_fifo_reconstructor.py
from __future__ import annotations

from datetime import datetime
from sqlmodel import select

from src.db.models import Account, Execution, Trade, TradeDay
from src.domain.reconstructor import TradeReconstructor


def test_fifo_realized_pnl_correctness(session):
    # IMPORTANT: TradeReconstructor.reconstruct_for_account() expects "account_id"
    # which in your schema is Account.id (UUID string), not account_number.
    acct = Account(account_number="U1234567", currency="USD")
    session.add(acct)
    session.commit()
    session.refresh(acct)

    account_id = acct.id

    # Scenario:
    # Buy 10 @ 100 (comm -1.0), Buy 10 @ 110 (comm -1.0), Sell 15 @ 120 (comm -1.5)
    # FIFO realized gross = 10*(120-100) + 5*(120-110) = 250
    # Total commissions = -3.5, realized net = 246.5
    exes = [
        Execution(
            account_id=account_id,
            ib_execution_id="E1",
            conid=265598,
            symbol="AAPL",
            ts_utc=datetime(2025, 1, 2, 14, 30, 0),  # naive UTC
            ts_raw="2025-01-02;09:30:00 US/Eastern",
            side="BUY",
            quantity=10.0,
            price=100.0,
            commission=-1.0,
        ),
        Execution(
            account_id=account_id,
            ib_execution_id="E2",
            conid=265598,
            symbol="AAPL",
            ts_utc=datetime(2025, 1, 2, 14, 31, 0),
            ts_raw="2025-01-02;09:31:00 US/Eastern",
            side="BUY",
            quantity=10.0,
            price=110.0,
            commission=-1.0,
        ),
        Execution(
            account_id=account_id,
            ib_execution_id="E3",
            conid=265598,
            symbol="AAPL",
            ts_utc=datetime(2025, 1, 2, 15, 0, 0),
            ts_raw="2025-01-02;10:00:00 US/Eastern",
            side="SELL",
            quantity=15.0,
            price=120.0,
            commission=-1.5,
        ),
    ]
    session.add_all(exes)
    session.commit()

    trades_created, trade_days_created = TradeReconstructor.reconstruct_for_account(
        session=session,
        account_id=account_id,
        report_timezone="US/Eastern",
    )

    assert trades_created == 1
    assert trade_days_created == 1

    trades = session.exec(select(Trade).where(Trade.account_id == account_id)).all()
    assert len(trades) == 1
    trade = trades[0]

    assert trade.direction == "LONG"
    assert trade.status == "open"  # still has 5 shares remaining open
    assert trade.quantity_opened == 20.0
    assert trade.quantity_closed == 15.0
    assert round(trade.gross_pnl_total, 6) == 250.0
    assert round(trade.commission_total, 6) == -3.5
    assert round(trade.net_pnl_total, 6) == 0.0  # net_pnl_total set only when trade fully closes in your code

    tds = session.exec(select(TradeDay).where(TradeDay.trade_id == trade.id)).all()
    assert len(tds) == 1
    td = tds[0]

    assert td.shares_closed == 15.0
    assert round(td.realized_gross, 6) == 250.0
    assert round(td.commissions, 6) == -3.5
    assert round(td.realized_net, 6) == 246.5
    assert td.day_status in ("adjusted", "closed")
