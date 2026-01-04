# streamlit_app.py
"""Main entry point for Streamlit app."""

import streamlit as st

st.set_page_config(
    page_title="Trading Journal",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)

from src.ui.app import init_session_state, main_app

init_session_state()
main_app()
