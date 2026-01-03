# streamlit_app.py
"""Main entry point for Streamlit app."""

from src.ui.app import init_session_state, main_app

init_session_state()
main_app()
