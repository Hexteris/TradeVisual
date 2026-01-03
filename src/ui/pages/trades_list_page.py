# src/ui/pages/trades_list_page.py
"""Trades list page - all trades with filters."""

import streamlit as st
import pandas as pd
from sqlmodel import select
from zoneinfo import ZoneInfo
from datetime import timezone as dt_timezone, date

from src.db.models import Trade
from src.db.session import get_session
from src.ui.helpers.current_context import require_account_id


def render():
    """Render trades list page."""
    st.subheader("Trades List")

    account_id = require_account_id()

    # Get all trades
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

    # Get unique symbols
    unique_symbols = sorted(list(set(t.symbol for t in trades)))

    # Get date range from trades
    all_dates = [t.opened_at_utc.date() for t in trades if t.opened_at_utc]
    min_date = min(all_dates) if all_dates else date.today()
    max_date = max(all_dates) if all_dates else date.today()

    # Filters row 1
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

    # Filters row 2
    col1, col2, col3 = st.columns(3)

    with col1:
        symbol_filter = st.multiselect(
            "Symbols",
            unique_symbols,
            default=unique_symbols,
        )

    with col2:
        start_date = st.date_input(
            "Start Date",
            value=min_date,
            min_value=min_date,
            max_value=max_date,
        )

    with col3:
        end_date = st.date_input(
            "End Date",
            value=max_date,
            min_value=min_date,
            max_value=max_date,
        )

        # Apply filters - handle empty lists as "show all"
    filtered_trades = []
    
    for t in trades:
        # If filter is empty, treat as "all selected"
        if status_filter and t.status not in status_filter:
            continue
        if direction_filter and t.direction not in direction_filter:
            continue
        if symbol_filter and t.symbol not in symbol_filter:
            continue
        if t.opened_at_utc.date() < start_date or t.opened_at_utc.date() > end_date:
            continue
        
        filtered_trades.append(t)

    # Apply P&L filter
    if pnl_filter == "Winners":
        filtered_trades = [t for t in filtered_trades if t.net_pnl_total > 0]
    elif pnl_filter == "Losers":
        filtered_trades = [t for t in filtered_trades if t.net_pnl_total < 0]


    # Get timezone
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
            "Gross P&L": trade.gross_pnl_total,
            "Commissions": trade.commission_total,
            "Net P&L": trade.net_pnl_total,
        })

    df = pd.DataFrame(rows)
    
    # Add sorting controls
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        sort_by = st.selectbox(
            "Sort by",
            ["Opened", "Net P&L", "Symbol", "Gross P&L"],
            index=0,
        )
    with col2:
        sort_order = st.selectbox("Order", ["Descending", "Ascending"])
    
    # Sort dataframe
    ascending = (sort_order == "Ascending")
    df = df.sort_values(by=sort_by, ascending=ascending)
    
    # Format currency columns for display
    df_display = df.copy()
    df_display["Gross P&L"] = df_display["Gross P&L"].apply(lambda x: f"${x:.2f}")
    df_display["Commissions"] = df_display["Commissions"].apply(lambda x: f"${x:.2f}")
    df_display["Net P&L"] = df_display["Net P&L"].apply(lambda x: f"${x:.2f}")

    # CSV Export button
    if not df.empty:
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 Export to CSV",
            data=csv,
            file_name=f"trades_{start_date}_{end_date}.csv",
            mime="text/csv",
        )

    st.dataframe(df_display, use_container_width=True, hide_index=True)

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
