# src/ui/pages/trades_list_page.py
"""Trades list page - all trades with filters."""

import streamlit as st
from sqlmodel import Session, select
import pandas as pd

from src.db.models import Trade, TradeExecution, Execution


def render(session: Session):
    """Render trades list page."""
    st.subheader("📊 Trades List")
    
    account = st.session_state.get("account")
    if not account:
        st.error("No account selected")
        return
    
    # Get all trades
    stmt = select(Trade).where(Trade.account_id == account.id).order_by(Trade.opened_at_utc.desc())
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
    
    # Build table
    rows = []
    for trade in filtered_trades:
        rows.append({
            "Symbol": trade.symbol,
            "Direction": trade.direction,
            "Opened": trade.opened_at_utc.strftime("%Y-%m-%d %H:%M"),
            "Closed": trade.closed_at_utc.strftime("%Y-%m-%d %H:%M") if trade.closed_at_utc else "Open",
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
    winners = len([t for t in filtered_trades if t.net_pnl_total > 0])
    total_pnl = sum(t.net_pnl_total for t in filtered_trades)
    total_commissions = sum(t.commission_total for t in filtered_trades)
    
    col1.metric("Total Trades", total_trades)
    col2.metric("Winning Trades", winners)
    col3.metric("Total P&L", f"${total_pnl:.2f}")
    col4.metric("Total Commissions", f"${total_commissions:.2f}")
