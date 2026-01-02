"""
SQLModel definitions for trading journal.
Session-only in-memory SQLite (no auth, no persistence).
"""

from datetime import datetime, date, timezone
from typing import Optional, List
import uuid
import pytz

from sqlmodel import SQLModel, Field, Relationship


class Account(SQLModel, table=True):
    """IBKR Account (one per uploaded report in this MVP)."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    account_number: str = Field(index=True)  # e.g., U12345678
    currency: str = Field(default="USD")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    executions: List["Execution"] = Relationship(back_populates="account", cascade_delete=True)
    trades: List["Trade"] = Relationship(back_populates="account", cascade_delete=True)


class Execution(SQLModel, table=True):
    """Individual trade execution (buy/sell) from IBKR Flex Query."""
    __tablename__ = "execution"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    account_id: str = Field(foreign_key="account.id", index=True)

    ib_execution_id: str = Field(index=True)  # Trade ID from IBKR
    conid: Optional[int] = Field(default=None, index=True)
    symbol: str = Field(index=True)

    ts_utc: datetime = Field(index=True)  # stored as naive UTC
    ts_raw: str = Field()  # raw string from IBKR

    side: str = Field()  # BUY or SELL
    quantity: float = Field()
    price: float = Field()
    commission: float = Field()  # Negative in IBKR data

    exchange: Optional[str] = Field(default=None)
    order_type: Optional[str] = Field(default=None)
    order_time_utc: Optional[datetime] = Field(default=None)
    currency: str = Field(default="USD")

    __table_args__ = (
        __import__("sqlalchemy").UniqueConstraint(
            "account_id", "ib_execution_id", name="uq_account_ib_exec"
        ),
    )

    account: Account = Relationship(back_populates="executions")
    trade_executions: List["TradeExecution"] = Relationship(
        back_populates="execution", cascade_delete=True
    )

    @property
    def ts_utc_aware(self):
        """ts_utc stored as naive but representing UTC."""
        return self.ts_utc.replace(tzinfo=timezone.utc)

    @property
    def ts_sg(self):
        """ts_utc converted to Asia/Singapore."""
        sg = pytz.timezone("Asia/Singapore")
        return self.ts_utc_aware.astimezone(sg)


class Trade(SQLModel, table=True):
    """Reconstructed trade (may span multiple executions due to partial fills)."""
    __tablename__ = "trade"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    account_id: str = Field(foreign_key="account.id", index=True)

    symbol: str = Field(index=True)
    conid: Optional[int] = Field(default=None, index=True)

    direction: str = Field()  # LONG or SHORT

    opened_at_utc: datetime = Field(index=True)
    closed_at_utc: Optional[datetime] = Field(default=None, index=True)

    status: str = Field(default="open")  # open, closed

    gross_pnl_total: float = Field(default=0.0)
    commission_total: float = Field(default=0.0)
    net_pnl_total: float = Field(default=0.0)

    quantity_opened: float = Field()
    quantity_closed: float = Field(default=0.0)

    notes: str = Field(default="")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    account: Account = Relationship(back_populates="trades")
    trade_executions: List["TradeExecution"] = Relationship(
        back_populates="trade", cascade_delete=True
    )
    trade_days: List["TradeDay"] = Relationship(back_populates="trade", cascade_delete=True)
    tags: List["TradeTag"] = Relationship(back_populates="trade", cascade_delete=True)


class TradeExecution(SQLModel, table=True):
    """Link between Trade and Execution (how much from each exec went to this trade)."""
    __tablename__ = "trade_execution"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    trade_id: str = Field(foreign_key="trade.id", index=True)
    execution_id: str = Field(foreign_key="execution.id", index=True)

    signed_qty: float = Field()
    role: str = Field()  # "open" or "close"
    lot_match_group: Optional[str] = Field(default=None)

    trade: Trade = Relationship(back_populates="trade_executions")
    execution: Execution = Relationship(back_populates="trade_executions")


class TradeDay(SQLModel, table=True):
    """Daily P&L summary for a trade (multi-day partial closes)."""
    __tablename__ = "trade_day"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    trade_id: str = Field(foreign_key="trade.id", index=True)

    day_date_local: date = Field(index=True)  # date in report_timezone
    day_status: str = Field()  # "opened", "adjusted", "closed"

    realized_gross: float = Field(default=0.0)
    commissions: float = Field(default=0.0)
    realized_net: float = Field(default=0.0)

    shares_closed: float = Field(default=0.0)

    trade: Trade = Relationship(back_populates="trade_days")


class Tag(SQLModel, table=True):
    """Trade tags (kept for future; currently optional)."""
    __tablename__ = "tag"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    account_id: str = Field(foreign_key="account.id", index=True)
    name: str = Field()

    __table_args__ = (
        __import__("sqlalchemy").UniqueConstraint("account_id", "name", name="uq_account_tag"),
    )

    trade_tags: List["TradeTag"] = Relationship(back_populates="tag", cascade_delete=True)


class TradeTag(SQLModel, table=True):
    """Association between Trade and Tag."""
    __tablename__ = "trade_tag"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    trade_id: str = Field(foreign_key="trade.id", index=True)
    tag_id: str = Field(foreign_key="tag.id", index=True)

    __table_args__ = (
        __import__("sqlalchemy").UniqueConstraint("trade_id", "tag_id", name="uq_trade_tag"),
    )

    trade: Trade = Relationship(back_populates="tags")
    tag: Tag = Relationship(back_populates="trade_tags")
