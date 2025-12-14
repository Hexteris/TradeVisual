# src/domain/reconstructor.py
"""
Trade reconstruction from executions.
Implements FIFO lot matching, partial closes, position tracking, and flips.
"""

from typing import Dict, List, Tuple, Optional
from datetime import datetime
from collections import defaultdict, deque
import pytz

from sqlmodel import Session, select
from src.db.models import Execution, Trade, TradeExecution, TradeDay
from src.domain.models import PositionState, OpenLot


class TradeReconstructor:
    """Reconstructs trades from executions using FIFO matching."""
    
    @staticmethod
    def reconstruct_for_account(
        session: Session,
        account_id: str,
        report_timezone: str = "US/Eastern",
    ) -> Tuple[int, int]:
        """
        Full reconstruction of trades from executions.
        Idempotent: deletes all existing trades/trade_days for account and rebuilds.
        
        Args:
            session: SQLModel session
            account_id: Account to reconstruct
            report_timezone: Timezone for grouping trades by day
        
        Returns:
            (trades_created, trade_days_created)
        """
        tz = pytz.timezone(report_timezone)
        
        # Delete existing trades (cascade deletes trade_executions, trade_days, trade_tags)
        session.query(Trade).filter(Trade.account_id == account_id).delete()
        
        # Get all executions sorted by time
        stmt = select(Execution).where(
            Execution.account_id == account_id
        ).order_by(Execution.ts_utc, Execution.ib_execution_id)
        
        executions = session.exec(stmt).all()
        
        if not executions:
            return 0, 0
        
        # Group by (conid or symbol)
        by_instrument = defaultdict(list)
        for exe in executions:
            key = (exe.conid, exe.symbol) if exe.conid else (None, exe.symbol)
            by_instrument[key].append(exe)
        
        trades_created = 0
        trade_days_created = 0
        
        # Reconstruct per instrument
        for (conid, symbol), exes in by_instrument.items():
            num_trades, num_days = TradeReconstructor._reconstruct_instrument(
                session=session,
                account_id=account_id,
                conid=conid,
                symbol=symbol,
                executions=exes,
                tz=tz,
            )
            trades_created += num_trades
            trade_days_created += num_days
        
        session.commit()
        return trades_created, trade_days_created
    
    @staticmethod
    def _reconstruct_instrument(
        session: Session,
        account_id: str,
        conid: Optional[int],
        symbol: str,
        executions: List[Execution],
        tz,
    ) -> Tuple[int, int]:
        """Reconstruct trades for a single instrument."""
        
        position = PositionState()  # Current position tracker
        trades_created = 0
        trade_days_created = 0
        
        for exe in executions:
            signed_qty = exe.quantity if exe.side == "BUY" else -exe.quantity
            
            # Check if position will flip
            if position.current_signed_qty != 0:
                current_sign = position.current_signed_qty > 0
                will_flip = (position.current_signed_qty + signed_qty) == 0 or \
                           ((position.current_signed_qty + signed_qty) * position.current_signed_qty < 0)
            else:
                will_flip = False
            
            if will_flip and position.current_signed_qty != 0:
                # Close existing trade at crossing point
                close_qty = -position.current_signed_qty
                
                num_days = TradeReconstructor._close_trade(
                    session=session,
                    trade_id=position.current_trade_id,
                    close_execution=exe,
                    close_qty=close_qty,
                    tz=tz,
                )
                trade_days_created += num_days
                
                # Reset position
                position.reset()
            
            # Now handle execution quantity (might be opening or closing)
            if position.current_signed_qty == 0:
                # Opening new position
                trade = Trade(
                    account_id=account_id,
                    symbol=symbol,
                    conid=conid,
                    direction="LONG" if signed_qty > 0 else "SHORT",
                    opened_at_utc=exe.ts_utc,
                    status="open",
                    quantity_opened=abs(signed_qty),
                    quantity_closed=0.0,
                )
                session.add(trade)
                session.flush()
                
                position.current_trade_id = trade.id
                position.current_signed_qty = signed_qty
                position.opened_at = exe.ts_utc
                position.open_lots = deque([OpenLot(qty=abs(signed_qty), price=exe.price, exe_id=exe.id)])
                
                # Create trade_execution for opening
                trade_exe = TradeExecution(
                    trade_id=trade.id,
                    execution_id=exe.id,
                    signed_qty=signed_qty,
                    role="open",
                )
                session.add(trade_exe)
                trades_created += 1
            
            else:
                # Partial close or continued position
                if (signed_qty > 0 and position.current_signed_qty > 0) or \
                   (signed_qty < 0 and position.current_signed_qty < 0):
                    # Same direction: adding to position
                    position.current_signed_qty += signed_qty
                    position.open_lots.append(
                        OpenLot(qty=abs(signed_qty), price=exe.price, exe_id=exe.id)
                    )
                    
                    # Track in trade_execution
                    trade_exe = TradeExecution(
                        trade_id=position.current_trade_id,
                        execution_id=exe.id,
                        signed_qty=signed_qty,
                        role="open",
                    )
                    session.add(trade_exe)
                
                else:
                    # Opposite direction: closing part of position
                    close_qty = min(abs(position.current_signed_qty), abs(signed_qty))
                    position.current_signed_qty += signed_qty
                    
                    # Match lots FIFO
                    remaining_to_close = close_qty
                    while remaining_to_close > 0 and position.open_lots:
                        lot = position.open_lots[0]
                        matched = min(lot.qty, remaining_to_close)
                        
                        realized_pnl = TradeReconstructor._compute_realized_pnl(
                            is_long=position.current_signed_qty + close_qty > 0,
                            open_price=lot.price,
                            close_price=exe.price,
                            qty=matched,
                        )
                        
                        remaining_to_close -= matched
                        lot.qty -= matched
                        
                        if lot.qty == 0:
                            position.open_lots.popleft()
                    
                    # Track close in trade_execution
                    trade_exe = TradeExecution(
                        trade_id=position.current_trade_id,
                        execution_id=exe.id,
                        signed_qty=signed_qty,
                        role="close",
                    )
                    session.add(trade_exe)
                    
                    # If fully closed, finalize trade
                    if position.current_signed_qty == 0:
                        num_days = TradeReconstructor._close_trade(
                            session=session,
                            trade_id=position.current_trade_id,
                            close_execution=exe,
                            close_qty=close_qty,
                            tz=tz,
                        )
                        trade_days_created += num_days
                        position.reset()
        
        session.flush()
        return trades_created, trade_days_created
    
    @staticmethod
    def _close_trade(
        session: Session,
        trade_id: str,
        close_execution: Execution,
        close_qty: float,
        tz,
    ) -> int:
        """Finalize a closed trade and create trade_day records."""
        
        trade: Trade = session.query(Trade).filter(Trade.id == trade_id).first()
        if not trade:
            return 0
        
        trade.closed_at_utc = close_execution.ts_utc
        trade.status = "closed"
        
        # Recompute aggregates
        TradeReconstructor._compute_trade_metrics(session, trade)
        
        # Create trade_day records from trade_executions
        num_days = TradeReconstructor._create_trade_days(session, trade, tz)
        
        return num_days
    
    @staticmethod
    def _compute_trade_metrics(session: Session, trade: Trade) -> None:
        """Compute total P&L and commissions for a trade."""
        
        trade_exes: List[TradeExecution] = session.query(TradeExecution).filter(
            TradeExecution.trade_id == trade.id
        ).all()
        
        executions_map = {te.execution_id: te for te in trade_exes}
        
        gross = 0.0
        commissions = 0.0
        
        for exe_id in executions_map:
            exe: Execution = session.query(Execution).filter(Execution.id == exe_id).first()
            if exe:
                commissions += exe.commission
        
        # For closed trades, compute gross P&L from entry/exit prices
        if trade.status == "closed":
            opens = [te for te in trade_exes if te.role == "open"]
            closes = [te for te in trade_exes if te.role == "close"]
            
            if opens and closes:
                avg_open = sum(
                    session.query(Execution).filter(Execution.id == te.execution_id).first().price * 
                    abs(te.signed_qty)
                    for te in opens
                ) / sum(abs(te.signed_qty) for te in opens)
                
                avg_close = sum(
                    session.query(Execution).filter(Execution.id == te.execution_id).first().price * 
                    abs(te.signed_qty)
                    for te in closes
                ) / sum(abs(te.signed_qty) for te in closes)
                
                is_long = trade.direction == "LONG"
                total_qty = sum(abs(te.signed_qty) for te in opens)
                
                if is_long:
                    gross = (avg_close - avg_open) * total_qty
                else:
                    gross = (avg_open - avg_close) * total_qty
        
        trade.gross_pnl_total = gross
        trade.commission_total = commissions
        trade.net_pnl_total = gross + commissions  # commission is negative
    
    @staticmethod
    def _create_trade_days(session: Session, trade: Trade, tz) -> int:
        """
        Create trade_day records for each day the trade had activity.
        """
        trade_exes: List[TradeExecution] = session.query(TradeExecution).filter(
            TradeExecution.trade_id == trade.id
        ).all()
        
        # Group by day
        by_day = defaultdict(list)
        for te in trade_exes:
            exe: Execution = session.query(Execution).filter(Execution.id == te.execution_id).first()
            exe_local = exe.ts_utc.astimezone(tz)
            day_key = exe_local.strftime("%Y-%m-%d")
            by_day[day_key].append((te, exe))
        
        num_days = 0
        for day_date, items in sorted(by_day.items()):
            # Determine day_status
            has_opens = any(te.role == "open" for te, _ in items)
            has_closes = any(te.role == "close" for te, _ in items)
            
            if has_opens and has_closes:
                day_status = "closed" if trade.status == "closed" else "adjusted"
            elif has_opens:
                day_status = "opened"
            else:
                day_status = "adjusted"
            
            # Compute day P&L
            day_gross = 0.0
            day_commissions = 0.0
            day_shares_closed = 0.0
            
            for te, exe in items:
                day_commissions += exe.commission
                if te.role == "close":
                    day_shares_closed += abs(te.signed_qty)
                    # Compute realized pnl for this close
                    # (simplified; FIFO would match to specific lots)
            
            day_net = day_gross + day_commissions
            
            trade_day = TradeDay(
                trade_id=trade.id,
                day_date_local=day_date,
                day_status=day_status,
                realized_gross=day_gross,
                commissions=day_commissions,
                realized_net=day_net,
                shares_closed=day_shares_closed,
            )
            session.add(trade_day)
            num_days += 1
        
        return num_days
    
    @staticmethod
    def _compute_realized_pnl(is_long: bool, open_price: float, close_price: float, qty: float) -> float:
        """Compute realized P&L for a matched lot."""
        if is_long:
            return (close_price - open_price) * qty
        else:
            return (open_price - close_price) * qty
