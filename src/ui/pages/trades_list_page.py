# src/ui/pages/trades_list_page.py
"""Trades list page - all trades with filters."""

import streamlit as st
import pandas as pd
from sqlmodel import select
from zoneinfo import ZoneInfo
from datetime import timezone as dt_timezone

from src.db.models import Trade
from src.db.session import get_session
from src.ui.helpers.current_context import require_account_id



def render():
    """Render trades list page."""
    st.subheader("📊 Trades List")

    account_id = require_account_id()

    # Get all trades (from current in-memory DB)
    with get_session() as session:
        stmt = (
            select(Trade)
            .where(Trade.account_id == account_id)
            .order_by(Trade.opened_at_utc.desc())
        )
        trades = session.exec(stmt).all()

    if not trades:
        st.info("No trades yet. Import IBKR data first.")
        return

    # Filters
    col1, col2, col3 = st.columns(3)

    with col1:
        status_filter = st.multiselect(
            "Status",
            ["open", "closed"],
            default=["open", "closed"],
        )

    with col2:
        direction_filter = st.multiselect(
            "Direction",
            ["LONG", "SHORT"],
            default=["LONG", "SHORT"],
        )

    with col3:
        pnl_filter = st.selectbox(
            "P&L",
            ["All", "Winners", "Losers"],
        )

    # Apply filters
    filtered_trades = [
        t for t in trades
        if t.status in status_filter and t.direction in direction_filter
    ]

    if pnl_filter == "Winners":
        filtered_trades = [t for t in filtered_trades if t.net_pnl_total > 0]
    elif pnl_filter == "Losers":
        filtered_trades = [t for t in filtered_trades if t.net_pnl_total < 0]

        # Get timezone from session
    tz_name = st.session_state.get("report_timezone", "US/Eastern")
    tz_obj = ZoneInfo(tz_name)
    
    # Build table
    rows = []
    for trade in filtered_trades:
        # Convert UTC to local timezone
        opened_utc = trade.opened_at_utc.replace(tzinfo=dt_timezone.utc)
        opened_local = opened_utc.astimezone(tz_obj)
        
        if trade.closed_at_utc:
            closed_utc = trade.closed_at_utc.replace(tzinfo=dt_timezone.utc)
            closed_local = closed_utc.astimezone(tz_obj)
            closed_display = closed_local.strftime("%Y-%m-%d %H:%M")
        else:
            closed_display = "Open"
        
        rows.append({
            "Symbol": trade.symbol,
            "Direction": trade.direction,
            "Opened": opened_local.strftime("%Y-%m-%d %H:%M"),
            "Closed": closed_display,
            "Status": trade.status,
            "Qty": trade.quantity_opened,
            "Gross P&L": f"${trade.gross_pnl_total:.2f}",
            "Commissions": f"${trade.commission_total:.2f}",
            "Net P&L": f"${trade.net_pnl_total:.2f}",
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Summary metrics
    st.divider()
    st.subheader("Summary")

    col1, col2, col3, col4 = st.columns(4)

    total_trades = len(filtered_trades)
    winners = sum(1 for t in filtered_trades if t.net_pnl_total > 0)
    total_pnl = sum(t.net_pnl_total for t in filtered_trades)
    total_commissions = sum(t.commission_total for t in filtered_trades)

    col1.metric("Total Trades", total_trades)
    col2.metric("Winning Trades", winners)
    col3.metric("Total P&L", f"${total_pnl:.2f}")
    col4.metric("Total Commissions", f"${total_commissions:.2f}")
