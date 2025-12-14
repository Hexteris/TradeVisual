# src/ui/pages/journal_page.py
"""Journal page - daily P&L view."""

import streamlit as st
from datetime import datetime, timedelta
import pytz
from sqlmodel import Session, select

from src.db.models import Trade, TradeDay
from src.domain.metrics import MetricsCalculator


def render(session: Session):
    """Render journal page."""
    st.subheader("📖 Journal - Daily P&L")
    
    account = st.session_state.get("account")
    if not account:
        st.error("No account selected")
        return
    
    tz = pytz.timezone(st.session_state.get("report_timezone", "US/Eastern"))
    
    # Get all trade_days for this account
    stmt = select(TradeDay).join(Trade).where(
        Trade.account_id == account.id
    ).order_by(TradeDay.day_date_local.desc())
    
    trade_days = session.exec(stmt).all()
    
    if not trade_days:
        st.info("No trades yet. Import IBKR data first.")
        return
    
    # Get unique dates
    unique_dates = sorted(set(td.day_date_local for td in trade_days), reverse=True)
    
    # Date selector
    selected_date = st.selectbox(
        "Select Date",
        unique_dates,
    )
    
    # Get summary for selected day
    summary = MetricsCalculator.get_daily_summary(
        session=session,
        account_id=account.id,
        day_date=selected_date,
    )
    
    # Display daily summary
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Gross P&L", f"${summary['gross_pnl']:.2f}")
    col2.metric("Commissions", f"${summary['commissions']:.2f}")
    col3.metric("Net P&L", f"${summary['net_pnl']:.2f}")
    col4.metric("Trades", summary['trades_count'])
    
    st.divider()
    
    # Get trades for this day
    stmt = select(TradeDay).where(
        TradeDay.day_date_local == selected_date
    )
    day_trade_days = session.exec(stmt).all()
    
    st.subheader("Trades on this day")
    
    for trade_day in day_trade_days:
        trade: Trade = session.query(Trade).filter(Trade.id == trade_day.trade_id).first()
        
        with st.expander(f"{trade.symbol} - {trade.direction} (Net: ${trade_day.realized_net:.2f})"):
            col1, col2, col3 = st.columns(3)
            col1.write(f"**Direction:** {trade.direction}")
            col2.write(f"**Opened:** {trade.opened_at_utc.strftime('%Y-%m-%d %H:%M:%S')} UTC")
            col3.write(f"**Status:** {trade.status}")
            
            st.write(f"**Gross P&L:** ${trade_day.realized_gross:.2f}")
            st.write(f"**Commissions:** ${trade_day.commissions:.2f}")
            st.write(f"**Net P&L:** ${trade_day.realized_net:.2f}")
            st.write(f"**Shares Closed:** {trade_day.shares_closed}")
            
            if trade.notes:
                st.write(f"**Notes:** {trade.notes}")
