# src/ui/pages/reports_page.py
"""Reports page - overview, instrument stats, and equity curve."""

import streamlit as st
import plotly.express as px
import pandas as pd

from src.db.session import get_session
from src.ui.helpers.current_context import require_account_id
from src.domain.metrics import MetricsCalculator


def render():
    """Render reports page."""
    st.subheader("Reports")

    account_id = require_account_id()

    report_type = st.selectbox(
        "Select Report",
        ["Overview", "Instrument Performance", "Equity Curve", "Time of Day (Entry)", "Price Levels"],
    )

    with get_session() as session:
        if report_type == "Overview":
            render_overview(session, account_id)
        elif report_type == "Instrument Performance":
            render_instrument_stats(session, account_id)
        elif report_type == "Equity Curve":
            render_equity_curve(session, account_id)
        elif report_type == "Time of Day (Entry)":
            render_time_of_day_entry(session, account_id)
        elif report_type == "Price Levels":
            render_price_levels(session, account_id)


def render_overview(session, account_id: str):
    st.subheader("Trading Overview")

    stats_net = MetricsCalculator.get_overview_stats(session, account_id, use_gross=False)
    stats_gross = MetricsCalculator.get_overview_stats(session, account_id, use_gross=True)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Closed Trades", stats_net["total_trades"])
    col2.metric("Win Rate", f"{stats_net['win_rate']:.1%}")
    col3.metric("Profit Factor", f"{stats_net['profit_factor']:.2f}")
    col4.metric("Total Net P&L", f"${stats_net['total_net']:.2f}")

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Gross", f"${stats_gross['total_gross']:.2f}")
        st.metric("Total Commissions", f"${stats_net['total_commissions']:.2f}")
    with col2:
        st.metric("Avg Win", f"${stats_net['avg_win']:.2f}")
        st.metric("Avg Loss", f"${stats_net['avg_loss']:.2f}")


def render_instrument_stats(session, account_id: str):
    st.subheader("Performance by Instrument")

    df = MetricsCalculator.get_instrument_stats(session, account_id)

    if df is None or df.empty:
        st.info("No closed trades yet.")
        return

    df = df.copy()
    df["win_rate"] = df["win_rate"].apply(lambda x: f"{x:.1%}")
    df["gross_pnl"] = df["gross_pnl"].apply(lambda x: f"${x:.2f}")
    df["commissions"] = df["commissions"].apply(lambda x: f"${x:.2f}")
    df["net_pnl"] = df["net_pnl"].apply(lambda x: f"${x:.2f}")

    st.dataframe(df, use_container_width=True, hide_index=True)


def render_equity_curve(session, account_id: str):
    st.subheader("Equity Curve")

    tz = st.session_state.report_timezone
    use_gross = st.checkbox("Show Gross (vs Net)", value=False)

    equity_curve = MetricsCalculator.get_equity_curve(
        session=session,
        account_id=account_id,
        report_timezone=tz,
        use_gross=use_gross, 
    )

    if equity_curve is None or equity_curve.empty:
        st.info("No trades yet.")
        return

    # After the change above, daily_pnl always matches the cumulative curve
    pnl_col = "daily_pnl"

    fig = px.line(
        equity_curve,
        x="date",
        y="cumulative_pnl",
        title="Cumulative P&L",
        labels={"cumulative_pnl": "Cumulative P&L ($)", "date": "Date"},
        markers=True,
    )
    st.plotly_chart(fig, use_container_width=True)

    fig_dd = px.area(
        equity_curve,
        x="date",
        y="drawdown",
        title="Drawdown",
        labels={"drawdown": "Drawdown ($)", "date": "Date"},
    )
    st.plotly_chart(fig_dd, use_container_width=True)

    fig_daily = px.bar(
        equity_curve,
        x="date",
        y=pnl_col,
        title="Daily P&L",
        labels={pnl_col: "Daily P&L ($)", "date": "Date"},
        color=pnl_col,
        color_continuous_scale=["red", "green"],
    )
    st.plotly_chart(fig_daily, use_container_width=True)


def render_time_of_day_entry(session, account_id: str):
    st.subheader("Time of Day (Entry)")

    tz = st.session_state.report_timezone
    use_gross = st.checkbox("Use Gross P&L (vs Net)", value=False)

    df = MetricsCalculator.get_entry_time_of_day_stats(
        session=session,
        account_id=account_id,
        report_timezone=tz,
        use_gross=use_gross,
    )

    if df is None or df.empty:
        st.info("No closed trades yet.")
        return

    df = df.copy()
    df["hour_label"] = df["hour"].apply(lambda h: f"{h:02d}:00")

    fig_trades = px.bar(
        df,
        x="hour_label",
        y="trades",
        title="Trades by Entry Hour",
        labels={"hour_label": "Entry Hour", "trades": "Number of Trades"},
    )
    st.plotly_chart(fig_trades, use_container_width=True)

    fig_pnl = px.bar(
        df,
        x="hour_label",
        y="pnl_sum",
        title="P&L by Entry Hour",
        labels={"hour_label": "Entry Hour", "pnl_sum": "Total P&L ($)"},
        color="pnl_sum",
        color_continuous_scale=["red", "green"],
    )
    st.plotly_chart(fig_pnl, use_container_width=True)

    st.dataframe(
        df[["hour_label", "trades", "pnl_sum", "pnl_avg", "win_rate"]],
        use_container_width=True,
        hide_index=True,
    )


def render_price_levels(session, account_id: str):
    st.subheader("Price Level Performance")

    use_gross = st.checkbox("Use Gross P&L (vs Net)", value=False)

    df = MetricsCalculator.get_price_bucket_stats(
        session=session,
        account_id=account_id,
        use_gross=use_gross,
    )

    if df is None or df.empty:
        st.info("No closed trades yet.")
        return

    df = df.copy()
    # Readable labels - e.g. $5-$10
    df["bucket_label"] = df["price_bucket"].apply(
        lambda x: f"${int(x.left)}-${int(x.right)}"
    )

    fig_trades = px.bar(
        df,
        x="bucket_label",
        y="trades",
        title="Trades by Price Bucket (Avg Entry Price)",
        labels={"bucket_label": "Avg Entry Price Bucket", "trades": "Number of Trades"},
    )
    st.plotly_chart(fig_trades, use_container_width=True)

    fig_pnl = px.bar(
        df,
        x="bucket_label",
        y="pnl_sum",
        title="P&L by Price Bucket",
        labels={"bucket_label": "Avg Entry Price Bucket", "pnl_sum": "Total P&L ($)"},
        color="pnl_sum",
        color_continuous_scale=["red", "green"],
    )
    st.plotly_chart(fig_pnl, use_container_width=True)

    df_display = df[["bucket_label", "trades", "pnl_sum", "pnl_avg"]].copy()
    df_display.columns = ["Price Range", "Trades", "Total P&L", "Avg P&L"]
    st.dataframe(df_display, use_container_width=True, hide_index=True)