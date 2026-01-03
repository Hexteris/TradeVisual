# src/ui/pages/journal_page.py
"""Journal page - daily P&L view."""

import streamlit as st
from sqlmodel import select
from zoneinfo import ZoneInfo
from datetime import timezone as dt_timezone

from src.db.session import get_session
from src.ui.helpers.current_context import require_account_id
from src.db.models import Trade, TradeDay
from src.domain.metrics import MetricsCalculator


def render():
    """Render journal page."""
    st.subheader("📖 Journal - Daily P&L")

    account_id = require_account_id()
    tz = st.session_state.report_timezone

    with get_session() as session:
        # Get all trade_days for this account (via Trade join)
        stmt = (
            select(TradeDay)
            .join(Trade)
            .where(Trade.account_id == account_id)
            .order_by(TradeDay.day_date_local.desc())
        )
        trade_days = session.exec(stmt).all()

        if not trade_days:
            st.info("No trades yet. Import IBKR data first.")
            return

        unique_dates = sorted({td.day_date_local for td in trade_days}, reverse=True)

        selected_date = st.selectbox("Select Date", unique_dates)

        summary = MetricsCalculator.get_daily_summary(
            session=session,
            account_id=account_id,
            day_date=selected_date,
        )

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Gross P&L", f"${summary['gross_pnl']:.2f}")
        col2.metric("Commissions", f"${summary['commissions']:.2f}")
        col3.metric("Net P&L", f"${summary['net_pnl']:.2f}")
        col4.metric("Trades", summary["trades_count"])

        st.divider()

        # Trades for this day (must still be restricted to this account)
        stmt = (
            select(TradeDay, Trade)
            .join(Trade, Trade.id == TradeDay.trade_id)
            .where(Trade.account_id == account_id)
            .where(TradeDay.day_date_local == selected_date)
            .order_by(Trade.opened_at_utc.asc())
        )
        rows = session.exec(stmt).all()

    st.subheader("Trades on this day")

    for trade_day, trade in rows:
        title = f"{trade.symbol} - {trade.direction} (Net: ${trade_day.realized_net:.2f})"
        with st.expander(title):
            c1, c2, c3 = st.columns(3)
            c1.write(f"**Direction:** {trade.direction}")
            # Convert UTC to local timezone
            tz_obj = ZoneInfo(tz)
            opened_utc = trade.opened_at_utc.replace(tzinfo=dt_timezone.utc)
            opened_local = opened_utc.astimezone(tz_obj)
            c2.write(f"**Opened:** {opened_local.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            c3.write(f"**Status:** {trade.status}")

            st.write(f"**Gross P&L:** ${trade_day.realized_gross:.2f}")
            st.write(f"**Commissions:** ${trade_day.commissions:.2f}")
            st.write(f"**Net P&L:** ${trade_day.realized_net:.2f}")
            st.write(f"**Shares Closed:** {trade_day.shares_closed}")

            if trade.notes:
                st.write(f"**Notes:** {trade.notes}")

    st.caption(f"Report timezone: {tz}")
