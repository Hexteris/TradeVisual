# src/ui/pages/calendar_page.py
"""Calendar page - monthly P&L heatmap."""


import calendar
from datetime import date


import pandas as pd
import streamlit as st
from sqlmodel import select


from src.db.models import Trade, TradeDay
from src.db.session import get_session
from src.ui.helpers.current_context import require_account_id



def render():
    st.subheader("Calendar P&L")
    
    account_id = require_account_id()

    use_gross = st.checkbox("Show Gross (vs Net)", value=False)

    # Find available months based on TradeDay dates for this account
    with get_session() as session:
        stmt_dates = (
            select(TradeDay.day_date_local)
            .join(Trade, Trade.id == TradeDay.trade_id)
            .where(Trade.account_id == account_id)
        )
        all_days = session.exec(stmt_dates).all()

    if not all_days:
        st.info("No trades yet. Import IBKR data first.")
        return

    # Build month options from available days
    day_series = pd.to_datetime(pd.Series(all_days))
    months = sorted(day_series.dt.to_period("M").unique())

    selected_month = st.selectbox(
        "Select Month",
        months,
        format_func=lambda p: p.strftime("%Y-%m"),
        index=len(months) - 1,  # default to most recent month
    )

    year = int(selected_month.year)
    month = int(selected_month.month)
    month_start = date(year, month, 1)
    month_end = date(year, month, calendar.monthrange(year, month)[1])

    # Pull TradeDays for the selected month (account-scoped)
    with get_session() as session:
        stmt = (
            select(TradeDay)
            .join(Trade, Trade.id == TradeDay.trade_id)
            .where(Trade.account_id == account_id)
            .where(TradeDay.day_date_local >= month_start)
            .where(TradeDay.day_date_local <= month_end)
        )
        trade_days = session.exec(stmt).all()

    # Aggregate pnl by date
    by_day_pnl = {}
    for td in trade_days:
        pnl = td.realized_gross if use_gross else td.realized_net
        by_day_pnl[td.day_date_local] = by_day_pnl.get(td.day_date_local, 0.0) + float(pnl)

    # Month summary
    month_total = sum(by_day_pnl.values())
    trading_days = len(by_day_pnl)
    avg_per_day = (month_total / trading_days) if trading_days else 0.0

    st.write(f"### {calendar.month_name[month]} {year}")

    c1, c2, c3 = st.columns(3)
    c1.metric("Month P&L", f"${month_total:.2f}")
    c2.metric("Trading days", trading_days)
    c3.metric("Avg / day", f"${avg_per_day:.2f}")

    st.divider()

    # Calendar grid
    cal = calendar.monthcalendar(year, month)

    # Day headers
    cols = st.columns(7)
    for i, day_name in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]):
        cols[i].write(f"**{day_name}**")

    # Cells
    for week in cal:
        cols = st.columns(7)
        for i, day_num in enumerate(week):
            if day_num == 0:
                cols[i].write("")
                continue

            d = date(year, month, day_num)
            pnl = by_day_pnl.get(d)

            if pnl is None:
                cols[i].write(str(day_num))
                continue

            # Use rgba for transparency instead of opacity
            bg_color = "rgba(0, 128, 0, 0.25)" if pnl > 0 else "rgba(255, 0, 0, 0.25)" if pnl < 0 else "rgba(128, 128, 128, 0.25)"
            
            with cols[i]:
                st.markdown(
                    f"""
                    <div style="background-color: {bg_color}; padding: 10px; border-radius: 6px;">
                      <div style="color: #262730; font-weight: 500; text-align: left;">{day_num}</div>
                      <div style="color: #262730; font-weight: 700; font-size: 16px; text-align: center; margin-top: 4px;">${pnl:.2f}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    st.caption(f"Mode: {'Gross' if use_gross else 'Net'} • Session-only data")
