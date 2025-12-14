# src/ui/pages/calendar_page.py
"""Calendar page - monthly P&L heatmap."""

import streamlit as st
from sqlmodel import Session, select
import pandas as pd
import calendar
from datetime import datetime

from src.db.models import Trade, TradeDay
from src.domain.metrics import MetricsCalculator


def render(session: Session):
    """Render calendar page."""
    st.subheader("📅 Calendar P&L")
    
    account = st.session_state.get("account")
    if not account:
        st.error("No account selected")
        return
    
    # Get equity curve to find date range
    equity_curve = MetricsCalculator.get_equity_curve(
        session=session,
        account_id=account.id,
        report_timezone=st.session_state.get("report_timezone", "US/Eastern"),
    )
    
    if equity_curve.empty:
        st.info("No trades yet. Import IBKR data first.")
        return
    
    # P&L toggle
    col1, col2 = st.columns(2)
    with col1:
        use_gross = st.checkbox("Show Gross (vs Net)", value=False)
    
    # Get unique months from equity curve
    equity_curve['date'] = pd.to_datetime(equity_curve['date'])
    equity_curve['year_month'] = equity_curve['date'].dt.to_period('M')
    unique_months = sorted(equity_curve['year_month'].unique())
    
    # Month selector
    selected_month = st.selectbox(
        "Select Month",
        unique_months,
        format_func=lambda x: x.strftime('%Y-%m'),
    )
    
    # Build calendar heatmap for selected month
    year = selected_month.year
    month = selected_month.month
    
    # Get all trade_days for the month
    month_start = f"{year:04d}-{month:02d}-01"
    month_end_day = calendar.monthrange(year, month)[1]
    month_end = f"{year:04d}-{month:02d}-{month_end_day:02d}"
    
    stmt = select(TradeDay).where(
        TradeDay.day_date_local >= month_start,
        TradeDay.day_date_local <= month_end,
    ).join(Trade).where(Trade.account_id == account.id)
    
    trade_days = session.exec(stmt).all()
    
    # Group by day
    by_day = {}
    for td in trade_days:
        if td.day_date_local not in by_day:
            by_day[td.day_date_local] = []
        by_day[td.day_date_local].append(td)
    
    # Build calendar grid
    cal = calendar.monthcalendar(year, month)
    
    # Header
    st.write(f"### {selected_month.strftime('%B %Y')}")
    
    # Day names
    cols = st.columns(7)
    for i, day_name in enumerate(['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']):
        cols[i].write(f"**{day_name}**")
    
    # Calendar cells
    for week in cal:
        cols = st.columns(7)
        for day_of_week, day in enumerate(week):
            if day == 0:
                cols[day_of_week].write("")
            else:
                day_str = f"{year:04d}-{month:02d}-{day:02d}"
                
                if day_str in by_day:
                    items = by_day[day_str]
                    if use_gross:
                        pnl = sum(td.realized_gross for td in items)
                    else:
                        pnl = sum(td.realized_net for td in items)
                    
                    # Color based on P&L
                    color = "green" if pnl > 0 else "red" if pnl < 0 else "gray"
                    
                    with cols[day_of_week]:
                        st.markdown(
                            f"""
                            <div style="background-color: {color}; opacity: 0.3; padding: 10px; border-radius: 5px; text-align: center;">
                            <b>{day}</b><br>
                            ${pnl:.2f}
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                else:
                    cols[day_of_week].write(str(day))
