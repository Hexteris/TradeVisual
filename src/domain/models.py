# src/domain/models.py
"""Domain value objects."""

from typing import Optional, Deque
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class OpenLot:
    """Represents an open lot (for FIFO matching)."""
    qty: float
    price: float
    exe_id: str


@dataclass
class PositionState:
    """Tracks current position for an instrument during reconstruction."""
    current_trade_id: Optional[str] = None
    current_signed_qty: float = 0.0  # Positive for LONG, negative for SHORT
    opened_at: Optional[datetime] = None
    open_lots: Deque[OpenLot] = field(default_factory=deque)
    
    def reset(self):
        """Reset position state."""
        self.current_trade_id = None
        self.current_signed_qty = 0.0
        self.opened_at = None
        self.open_lots = deque()
