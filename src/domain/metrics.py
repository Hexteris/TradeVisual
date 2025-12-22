# src/domain/metrics.py
"""Metrics and reporting calculations."""

from typing import Dict
from sqlmodel import Session, select
from datetime import datetime, timedelta
import pytz
import pandas as pd

from src.db.models import Trade, TradeDay, Execution, TradeExecution


class MetricsCalculator:
    """Calculate trading metrics and equity curve."""

    @staticmethod
    def get_equity_curve(
        session: Session,
        account_id: str,
        report_timezone: str = "US/Eastern",
        use_gross: bool = False,
    ) -> pd.DataFrame:
        """
        Build equity curve from daily trade_day P&L.

        Returns DataFrame with columns: date, daily_pnl, cumulative_pnl, drawdown, daily_gross
        """
        tz = pytz.timezone(report_timezone)

        stmt = (
            select(TradeDay)
            .join(Trade)
            .where(Trade.account_id == account_id)
            .order_by(TradeDay.day_date_local)
        )
        trade_days = session.exec(stmt).all()

        if not trade_days:
            return pd.DataFrame(
                columns=["date", "daily_pnl", "cumulative_pnl", "drawdown", "daily_gross"]
            )

        by_day = {}
        for td in trade_days:
            if td.day_date_local not in by_day:
                by_day[td.day_date_local] = []
            by_day[td.day_date_local].append(td)

        rows = []
        cumulative = 0.0
        peak = 0.0

        for day_date in sorted(by_day.keys()):
            items = by_day[day_date]

            daily_gross = sum(td.realized_gross for td in items)
            daily_commissions = sum(td.commissions for td in items)

            if use_gross:
                daily_pnl = daily_gross
            else:
                daily_pnl = daily_gross + daily_commissions

            cumulative += daily_pnl
            peak = max(peak, cumulative)
            drawdown = cumulative - peak if peak > 0 else 0.0

            rows.append(
                {
                    "date": day_date,
                    "daily_pnl": daily_pnl,
                    "daily_gross": daily_gross,
                    "cumulative_pnl": cumulative,
                    "drawdown": drawdown,
                }
            )

        return pd.DataFrame(rows)

    @staticmethod
    def get_daily_summary(
        session: Session,
        account_id: str,
        day_date: str,  # YYYY-MM-DD
    ) -> Dict:
        """Get summary metrics for a specific day."""
        stmt = select(TradeDay).join(Trade).where(
            Trade.account_id == account_id,
            TradeDay.day_date_local == day_date,
        )
        trade_days = session.exec(stmt).all()

        gross = sum(td.realized_gross for td in trade_days)
        commissions = sum(td.commissions for td in trade_days)
        net = sum(td.realized_net for td in trade_days)
        shares_closed = sum(td.shares_closed for td in trade_days)

        return {
            "date": day_date,
            "gross_pnl": gross,
            "commissions": commissions,
            "net_pnl": net,
            "trades_count": len(set(td.trade_id for td in trade_days)),
            "shares_closed": shares_closed,
        }

    @staticmethod
    def get_overview_stats(
        session: Session,
        account_id: str,
        use_gross: bool = False,
    ) -> Dict:
        """Get overall trading statistics."""
        stmt = select(Trade).where(
            Trade.account_id == account_id,
            Trade.status == "closed",
        )
        closed_trades = session.exec(stmt).all()

        if not closed_trades:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "total_gross": 0.0,
                "total_commissions": 0.0,
                "total_net": 0.0,
                "avg_win": 0.0,
                "avg_loss": 0.0,
                "profit_factor": 0.0,
            }

        wins = [t for t in closed_trades if t.net_pnl_total > 0]
        losses = [t for t in closed_trades if t.net_pnl_total < 0]

        total_gross = sum(t.gross_pnl_total for t in closed_trades)
        total_commissions = sum(t.commission_total for t in closed_trades)
        total_net = sum(t.net_pnl_total for t in closed_trades)

        gross_wins = sum(t.gross_pnl_total for t in wins)
        gross_losses = sum(abs(t.gross_pnl_total) for t in losses)

        profit_factor = gross_wins / gross_losses if gross_losses > 0 else 0.0

        return {
            "total_trades": len(closed_trades),
            "winning_trades": len(wins),
            "losing_trades": len(losses),
            "win_rate": len(wins) / len(closed_trades) if closed_trades else 0.0,
            "total_gross": total_gross,
            "total_commissions": total_commissions,
            "total_net": total_net,
            "avg_win": sum(t.net_pnl_total for t in wins) / len(wins) if wins else 0.0,
            "avg_loss": sum(t.net_pnl_total for t in losses) / len(losses) if losses else 0.0,
            "profit_factor": profit_factor,
        }

    @staticmethod
    def get_instrument_stats(
        session: Session,
        account_id: str,
    ) -> pd.DataFrame:
        """Get performance by instrument."""
        stmt = select(Trade).where(
            Trade.account_id == account_id,
            Trade.status == "closed",
        )
        trades = session.exec(stmt).all()

        by_symbol = {}
        for trade in trades:
            key = trade.symbol
            if key not in by_symbol:
                by_symbol[key] = []
            by_symbol[key].append(trade)

        rows = []
        for symbol, symbol_trades in sorted(by_symbol.items()):
            gross = sum(t.gross_pnl_total for t in symbol_trades)
            commissions = sum(t.commission_total for t in symbol_trades)
            net = sum(t.net_pnl_total for t in symbol_trades)

            wins = len([t for t in symbol_trades if t.net_pnl_total > 0])
            total = len(symbol_trades)

            rows.append(
                {
                    "symbol": symbol,
                    "count": total,
                    "wins": wins,
                    "win_rate": wins / total if total > 0 else 0.0,
                    "gross_pnl": gross,
                    "commissions": commissions,
                    "net_pnl": net,
                }
            )

        return pd.DataFrame(rows)

    @staticmethod
    def get_entry_time_of_day_stats(
        session: Session,
        account_id: str,
        report_timezone: str = "US/Eastern",
        use_gross: bool = False,
    ) -> pd.DataFrame:
        """Closed-trade performance grouped by ENTRY hour in report timezone."""
        tz = pytz.timezone(report_timezone)

        trades = session.exec(
            select(Trade).where(
                Trade.account_id == account_id,
                Trade.status == "closed",
            )
        ).all()

        if not trades:
            return pd.DataFrame(
                columns=["hour", "trades", "pnl_sum", "pnl_avg", "win_rate"]
            )

        rows = []
        for t in trades:
            entry_local = t.opened_at_utc.astimezone(tz)
            pnl = t.gross_pnl_total if use_gross else t.net_pnl_total
            rows.append(
                {"hour": entry_local.hour, "pnl": pnl, "is_win": 1 if pnl > 0 else 0}
            )

        df = pd.DataFrame(rows)
        out = (
            df.groupby("hour", as_index=False)
            .agg(
                trades=("pnl", "count"),
                pnl_sum=("pnl", "sum"),
                pnl_avg=("pnl", "mean"),
                win_rate=("is_win", "mean"),
            )
            .sort_values("hour")
        )
        return out

    @staticmethod
    def get_price_bucket_stats(
        session: Session,
        account_id: str,
        bucket_edges=None,
        use_gross: bool = False,
    ) -> pd.DataFrame:
        """
        Bucket closed trades by avg entry price and aggregate P&L + trade counts.
        """
        if bucket_edges is None:
            bucket_edges = [0, 5, 10, 20, 50, 100, 200, 500, 1000, 10_000]

        trades = session.exec(
            select(Trade).where(
                Trade.account_id == account_id,
                Trade.status == "closed",
            )
        ).all()

        if not trades:
            return pd.DataFrame(
                columns=["price_bucket", "trades", "pnl_sum", "pnl_avg"]
            )

        trade_ids = [t.id for t in trades]
        trade_map = {t.id: t for t in trades}

        rows = session.exec(
            select(TradeExecution, Execution)
            .join(Execution, TradeExecution.execution_id == Execution.id)
            .where(
                TradeExecution.trade_id.in_(trade_ids),
                TradeExecution.role == "open",
            )
        ).all()

        accum = {}  # trade_id -> (notional_sum, qty_sum)
        for te, exe in rows:
            qty = abs(te.signed_qty)
            if qty == 0:
                continue
            notional = exe.price * qty
            n, q = accum.get(te.trade_id, (0.0, 0.0))
            accum[te.trade_id] = (n + notional, q + qty)

        out_rows = []
        for trade_id, (notional_sum, qty_sum) in accum.items():
            if qty_sum <= 0:
                continue
            avg_entry = notional_sum / qty_sum
            t = trade_map[trade_id]
            pnl = t.gross_pnl_total if use_gross else t.net_pnl_total
            out_rows.append({"avg_entry": avg_entry, "pnl": pnl})

        df = pd.DataFrame(out_rows)
        if df.empty:
            return pd.DataFrame(
                columns=["price_bucket", "trades", "pnl_sum", "pnl_avg"]
            )

        df["price_bucket"] = pd.cut(
            df["avg_entry"], bins=bucket_edges, right=False, include_lowest=True
        )
        agg = (
            df.groupby("price_bucket", as_index=False)
            .agg(
                trades=("pnl", "count"),
                pnl_sum=("pnl", "sum"),
                pnl_avg=("pnl", "mean"),
            )
            .sort_values("price_bucket")
        )
        return agg
