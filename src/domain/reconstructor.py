# src/domain/reconstructor.py
"""Trade reconstruction from executions using FIFO matching."""

from typing import List, Tuple, Optional
from datetime import datetime, date, timezone
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
        Idempotent: deletes existing trades and rebuilds.
        
        Returns:
            (trades_created, trade_days_created)
        """
        tz = pytz.timezone(report_timezone)
        
        # Delete existing trades (cascades to trade_executions, trade_days, trade_tags)
        stmt = select(Trade).where(Trade.account_id == account_id)
        existing_trades = session.exec(stmt).all()
        for trade in existing_trades:
            session.delete(trade)
        session.commit()
        
        # Get all executions sorted by time
        stmt = select(Execution).where(
            Execution.account_id == account_id
        ).order_by(Execution.ts_utc, Execution.ib_execution_id)
        
        executions = session.exec(stmt).all()
        
        if not executions:
            return 0, 0
        
        # Group by instrument (conid or symbol)
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
    def _add_trade_execution(session: Session, trade_id: str, execution_id: str, signed_qty: float, role: str):
        if signed_qty is None:
            raise ValueError(f"signed_qty is None for trade_id={trade_id}, execution_id={execution_id}, role={role}")
        if signed_qty == 0:
            return
        session.add(
            TradeExecution(
                trade_id=trade_id,
                execution_id=execution_id,
                signed_qty=float(signed_qty),
                role=role,
            )
        )

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
        
        open_lots = deque()
        current_trade = None
        trades_created = 0
        trade_days_created = 0
        
        daily_pnl = defaultdict(lambda: {"gross": 0.0, "commissions": 0.0, "shares_closed": 0.0})
        
        for exe in executions:
            if not exe.ts_utc:
                continue
            try:
                exe_utc = exe.ts_utc.replace(tzinfo=timezone.utc)
                exe_local = exe_utc.astimezone(tz)
                raw_day = exe_local.date()
                
                # If execution is on weekend, roll back to Friday
                if raw_day.weekday() == 5:  # Saturday
                    day_key = date(raw_day.year, raw_day.month, raw_day.day - 1)
                elif raw_day.weekday() == 6:  # Sunday
                    day_key = date(raw_day.year, raw_day.month, raw_day.day - 2)
                else:
                    day_key = raw_day
            except Exception:
                continue
            if day_key is None:
                continue
         
            if exe.side == "BUY":
                if not current_trade or current_trade.direction == "SHORT":
                    if current_trade and current_trade.direction == "SHORT":
                        close_qty = min(exe.quantity, sum(lot.qty for lot in open_lots))
                        remaining = exe.quantity - close_qty
                        
                        to_close = close_qty
                        while to_close > 0 and open_lots:
                            lot = open_lots[0]
                            matched = min(lot.qty, to_close)
                            
                            pnl = (lot.price - exe.price) * matched
                            daily_pnl[(current_trade.id, day_key)]["gross"] += pnl
                            daily_pnl[(current_trade.id, day_key)]["shares_closed"] += matched
                            
                            current_trade.quantity_closed += matched
                            current_trade.gross_pnl_total += pnl
                            
                            to_close -= matched
                            lot.qty -= matched
                            if lot.qty == 0:
                                open_lots.popleft()
                        
                        daily_pnl[(current_trade.id, day_key)]["commissions"] += exe.commission
                        current_trade.commission_total += exe.commission
                        
                        if close_qty > 0:
                            TradeReconstructor._add_trade_execution(session, current_trade.id, exe.id, close_qty, "close")
                        
                        if len(open_lots) == 0:
                            current_trade.closed_at_utc = exe.ts_utc
                            current_trade.status = "closed"
                            current_trade.net_pnl_total = current_trade.gross_pnl_total + current_trade.commission_total
                            
                            trade_days_created += TradeReconstructor._finalize_trade_days(
                                session, current_trade, daily_pnl, tz
                            )
                            daily_pnl.clear()
                            current_trade = None
                        
                        if remaining > 0:
                            current_trade = Trade(
                                account_id=account_id,
                                symbol=symbol,
                                conid=conid,
                                direction="LONG",
                                opened_at_utc=exe.ts_utc,
                                status="open",
                                quantity_opened=remaining,
                                quantity_closed=0.0,
                                gross_pnl_total=0.0,
                                commission_total=exe.commission * (remaining / exe.quantity),
                                net_pnl_total=0.0,
                            )
                            session.add(current_trade)
                            session.flush()
                            trades_created += 1
                            
                            open_lots.append(OpenLot(qty=remaining, price=exe.price, exe_id=exe.id))
                            TradeReconstructor._add_trade_execution(session, current_trade.id, exe.id, remaining, "open")
                            daily_pnl[(current_trade.id, day_key)]["commissions"] += exe.commission * (remaining / exe.quantity)
                    else:
                        current_trade = Trade(
                            account_id=account_id,
                            symbol=symbol,
                            conid=conid,
                            direction="LONG",
                            opened_at_utc=exe.ts_utc,
                            status="open",
                            quantity_opened=exe.quantity,
                            quantity_closed=0.0,
                            gross_pnl_total=0.0,
                            commission_total=exe.commission,
                            net_pnl_total=0.0,
                        )
                        session.add(current_trade)
                        session.flush()
                        trades_created += 1
                        
                        open_lots.append(OpenLot(qty=exe.quantity, price=exe.price, exe_id=exe.id))
                        TradeReconstructor._add_trade_execution(session, current_trade.id, exe.id, exe.quantity, "open")
                        daily_pnl[(current_trade.id, day_key)]["commissions"] += exe.commission
                else:
                    current_trade.quantity_opened += exe.quantity
                    current_trade.commission_total += exe.commission
                    open_lots.append(OpenLot(qty=exe.quantity, price=exe.price, exe_id=exe.id))
                    TradeReconstructor._add_trade_execution(session, current_trade.id, exe.id, exe.quantity, "open")
                    daily_pnl[(current_trade.id, day_key)]["commissions"] += exe.commission
            
            else:  # SELL
                if not current_trade or current_trade.direction == "LONG":
                    if current_trade and current_trade.direction == "LONG":
                        close_qty = min(exe.quantity, sum(lot.qty for lot in open_lots))
                        remaining = exe.quantity - close_qty
                        
                        to_close = close_qty
                        while to_close > 0 and open_lots:
                            lot = open_lots[0]
                            matched = min(lot.qty, to_close)
                            
                            pnl = (exe.price - lot.price) * matched
                            daily_pnl[(current_trade.id, day_key)]["gross"] += pnl
                            daily_pnl[(current_trade.id, day_key)]["shares_closed"] += matched
                            
                            current_trade.quantity_closed += matched
                            current_trade.gross_pnl_total += pnl
                            
                            to_close -= matched
                            lot.qty -= matched
                            if lot.qty == 0:
                                open_lots.popleft()
                        
                        daily_pnl[(current_trade.id, day_key)]["commissions"] += exe.commission
                        current_trade.commission_total += exe.commission
                        
                        if close_qty > 0:
                            TradeReconstructor._add_trade_execution(session, current_trade.id, exe.id, -close_qty, "close")
                        
                        if len(open_lots) == 0:
                            current_trade.closed_at_utc = exe.ts_utc
                            current_trade.status = "closed"
                            current_trade.net_pnl_total = current_trade.gross_pnl_total + current_trade.commission_total
                            
                            trade_days_created += TradeReconstructor._finalize_trade_days(
                                session, current_trade, daily_pnl, tz
                            )
                            daily_pnl.clear()
                            current_trade = None
                        
                        if remaining > 0:
                            current_trade = Trade(
                                account_id=account_id,
                                symbol=symbol,
                                conid=conid,
                                direction="SHORT",
                                opened_at_utc=exe.ts_utc,
                                status="open",
                                quantity_opened=remaining,
                                quantity_closed=0.0,
                                gross_pnl_total=0.0,
                                commission_total=exe.commission * (remaining / exe.quantity),
                                net_pnl_total=0.0,
                            )
                            session.add(current_trade)
                            session.flush()
                            trades_created += 1
                            
                            open_lots.append(OpenLot(qty=remaining, price=exe.price, exe_id=exe.id))
                            TradeReconstructor._add_trade_execution(session, current_trade.id, exe.id, -remaining, "open")
                            daily_pnl[(current_trade.id, day_key)]["commissions"] += exe.commission * (remaining / exe.quantity)
                    else:
                        current_trade = Trade(
                            account_id=account_id,
                            symbol=symbol,
                            conid=conid,
                            direction="SHORT",
                            opened_at_utc=exe.ts_utc,
                            status="open",
                            quantity_opened=exe.quantity,
                            quantity_closed=0.0,
                            gross_pnl_total=0.0,
                            commission_total=exe.commission,
                            net_pnl_total=0.0,
                        )
                        session.add(current_trade)
                        session.flush()
                        trades_created += 1
                        
                        open_lots.append(OpenLot(qty=exe.quantity, price=exe.price, exe_id=exe.id))
                        TradeReconstructor._add_trade_execution(session, current_trade.id, exe.id, -exe.quantity, "open")
                        daily_pnl[(current_trade.id, day_key)]["commissions"] += exe.commission
                else:
                    current_trade.quantity_opened += exe.quantity
                    current_trade.commission_total += exe.commission
                    open_lots.append(OpenLot(qty=exe.quantity, price=exe.price, exe_id=exe.id))
                    TradeReconstructor._add_trade_execution(session, current_trade.id, exe.id, -exe.quantity, "open")
                    daily_pnl[(current_trade.id, day_key)]["commissions"] += exe.commission
        
        if current_trade and daily_pnl:
            trade_days_created += TradeReconstructor._finalize_trade_days(
                session, current_trade, daily_pnl, tz
            )
        
        return trades_created, trade_days_created
    
    @staticmethod
    def _finalize_trade_days(session: Session, trade: Trade, daily_pnl: dict, tz) -> int:
        """Create TradeDay records from accumulated daily P&L."""
        count = 0
        for (trade_id, day_date), pnl_data in daily_pnl.items():
            if trade_id != trade.id:
                continue
            if day_date is None:
                continue
            if pnl_data.get("shares_closed", 0.0) <= 0:
                continue
        
            trade_day = TradeDay(
                trade_id=trade.id,
                day_date_local=day_date,
                day_status="closed" if trade.status == "closed" else "adjusted",
                realized_gross=pnl_data.get("gross", 0.0),
                commissions=pnl_data.get("commissions", 0.0),
                realized_net=pnl_data.get("gross", 0.0) + pnl_data.get("commissions", 0.0),
                shares_closed=pnl_data.get("shares_closed", 0.0),
            )
            session.add(trade_day)
            count += 1
        
        return count
