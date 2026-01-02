# src/ui/app.py
"""Main Streamlit application"""

import streamlit as st

from src.ui.pages import import_page, journal_page, calendar_page, trades_list_page, reports_page


st.set_page_config(
    page_title="Trading Journal",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


def init_session_state():
    # Minimal session state for a stateless, per-upload app.
    if "account_id" not in st.session_state:
        st.session_state.account_id = None
    if "report_timezone" not in st.session_state:
        st.session_state.report_timezone = "Asia/Singapore"


def main_app():
    st.title("Trading Journal")

    with st.sidebar:
        st.header("⚙️ Settings")

        tz_options = ["Asia/Singapore", "US/Eastern", "US/Central", "US/Mountain", "US/Pacific", "UTC"]
        st.session_state.report_timezone = st.selectbox(
            "Report Timezone",
            tz_options,
            index=tz_options.index(st.session_state.report_timezone),
        )

        st.divider()
        st.caption("Session-only: data lives in memory for this tab and is reset when you upload another XML or refresh.")

    page = st.selectbox("Navigate", ["Import", "Trades List", "Reports", "Calendar", "Journal"])

    if page == "Import":
        import_page.render()
        return

    # All other pages require imported data (account_id present)
    if not st.session_state.account_id:
        st.warning("Import an XML first.")
        return

    if page == "Trades List":
        trades_list_page.render()
    elif page == "Reports":
        reports_page.render()
    elif page == "Calendar":
        calendar_page.render()
    elif page == "Journal":
        journal_page.render()


if __name__ == "__main__":
    init_session_state()
    main_app()
