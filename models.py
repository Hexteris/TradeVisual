# src/db/models.py
"""
SQLModel definitions for trading journal.
Designed for SQLite locally, Neon PostgreSQL in production.
"""

from datetime import datetime
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship, Column, String, DateTime, Float
import uuid


class User(SQLModel, table=True):
    """User accounts for multi-tenant support."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    username: str = Field(unique=True, index=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    accounts: List["Account"] = Relationship(back_populates="user")
    settings: List["UserSetting"] = Relationship(back_populates="user", cascade_delete=True)


class Account(SQLModel, table=True):
    """IBKR Account (typically one per user)."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    user_id: str = Field(foreign_key="user.id", index=True)
    account_number: str = Field(index=True)  # e.g., U12345678
    currency: str = Field(default="USD")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    user: User = Relationship(back_populates="accounts")
    executions: List["Execution"] = Relationship(back_populates="account", cascade_delete=True)
    trades: List["Trade"] = Relationship(back_populates="account", cascade_delete=True)


class Execution(SQLModel, table=True):
    """Individual trade execution (buy/sell) from IBKR Flex Query."""
    __tablename__ = "execution"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    account_id: str = Field(foreign_key="account.id", index=True)
    
    # IBKR identifiers (unique constraint on account + ib_exec_id prevents duplicates)
    ib_execution_id: str = Field(index=True)  # Trade ID from IBKR
    conid: Optional[int] = Field(default=None, index=True)  # Contract ID
    symbol: str = Field(index=True)
    
    # Timestamp (stored in UTC)
    ts_utc: datetime = Field(index=True)
    ts_raw: str = Field()  # Raw string from IBKR (for audit)
    
    # Trade details
    side: str = Field()  # BUY or SELL
    quantity: float = Field()
    price: float = Field()
    commission: float = Field()  # Negative in IBKR data
    
    # Optional fields from IBKR
    exchange: Optional[str] = Field(default=None)
    order_type: Optional[str] = Field(default=None)
    order_time_utc: Optional[datetime] = Field(default=None)
    currency: str = Field(default="USD")
    
    # Unique constraint: (account_id, ib_execution_id)
    __table_args__ = (
        __import__('sqlalchemy').UniqueConstraint('account_id', 'ib_execution_id', name='uq_account_ib_exec'),
    )
    
    account: Account = Relationship(back_populates="executions")
    trade_executions: List["TradeExecution"] = Relationship(back_populates="execution", cascade_delete=True)


class Trade(SQLModel, table=True):
    """Reconstructed trade (may span multiple executions due to partial fills)."""
    __tablename__ = "trade"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    account_id: str = Field(foreign_key="account.id", index=True)
    
    symbol: str = Field(index=True)
    conid: Optional[int] = Field(default=None, index=True)
    
    direction: str = Field()  # LONG or SHORT
    
    # Lifecycle timestamps (UTC)
    opened_at_utc: datetime = Field(index=True)
    closed_at_utc: Optional[datetime] = Field(default=None, index=True)
    
    status: str = Field(default="open")  # open, closed
    
    # Aggregated metrics (computed from trade_executions)
    gross_pnl_total: float = Field(default=0.0)
    commission_total: float = Field(default=0.0)
    net_pnl_total: float = Field(default=0.0)
    
    # Position tracking
    quantity_opened: float = Field()  # Total qty of opening leg
    quantity_closed: float = Field(default=0.0)  # Total qty closed so far
    
    notes: str = Field(default="")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    account: Account = Relationship(back_populates="trades")
    trade_executions: List["TradeExecution"] = Relationship(back_populates="trade", cascade_delete=True)
    trade_days: List["TradeDay"] = Relationship(back_populates="trade", cascade_delete=True)
    tags: List["TradeTag"] = Relationship(back_populates="trade", cascade_delete=True)


class TradeExecution(SQLModel, table=True):
    """Link between Trade and Execution (records how many shares from each exec went to this trade)."""
    __tablename__ = "trade_execution"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    trade_id: str = Field(foreign_key="trade.id", index=True)
    execution_id: str = Field(foreign_key="execution.id", index=True)
    
    signed_qty: float = Field()  # Quantity attributed to this trade (positive if same direction, negative if closing)
    role: str = Field()  # "open" or "close"
    lot_match_group: Optional[str] = Field(default=None)  # For FIFO tracking
    
    trade: Trade = Relationship(back_populates="trade_executions")
    execution: Execution = Relationship(back_populates="trade_executions")


class TradeDay(SQLModel, table=True):
    """Daily P&L summary for a trade (handles multi-day partial closes)."""
    __tablename__ = "trade_day"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    trade_id: str = Field(foreign_key="trade.id", index=True)
    
    day_date_local: str = Field(index=True)  # YYYY-MM-DD in report_timezone
    
    day_status: str = Field()  # "opened", "adjusted", "closed"
    
    # P&L for this day (can be partial if trade closes over multiple days)
    realized_gross: float = Field(default=0.0)
    commissions: float = Field(default=0.0)  # Allocated commission for this day
    realized_net: float = Field(default=0.0)  # gross + commissions
    
    shares_closed: float = Field(default=0.0)  # How many shares closed on this day
    
    trade: Trade = Relationship(back_populates="trade_days")


class Tag(SQLModel, table=True):
    """Trade tags (e.g., "scalp", "swing", "earnings play")."""
    __tablename__ = "tag"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    account_id: str = Field(foreign_key="account.id", index=True)
    name: str = Field()
    
    __table_args__ = (
        __import__('sqlalchemy').UniqueConstraint('account_id', 'name', name='uq_account_tag'),
    )
    
    trade_tags: List["TradeTag"] = Relationship(back_populates="tag", cascade_delete=True)


class TradeTag(SQLModel, table=True):
    """Association between Trade and Tag."""
    __tablename__ = "trade_tag"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    trade_id: str = Field(foreign_key="trade.id", index=True)
    tag_id: str = Field(foreign_key="tag.id", index=True)
    
    __table_args__ = (
        __import__('sqlalchemy').UniqueConstraint('trade_id', 'tag_id', name='uq_trade_tag'),
    )
    
    trade: Trade = Relationship(back_populates="tags")
    tag: Tag = Relationship(back_populates="trade_tags")


class UserSetting(SQLModel, table=True):
    """User preferences (timezone, display settings, etc.)."""
    __tablename__ = "user_setting"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    user_id: str = Field(foreign_key="user.id", index=True)
    
    key: str = Field()  # e.g., "report_timezone"
    value: str = Field()  # e.g., "US/Eastern"
    
    __table_args__ = (
        __import__('sqlalchemy').UniqueConstraint('user_id', 'key', name='uq_user_setting'),
    )
    
    user: User = Relationship(back_populates="settings")
