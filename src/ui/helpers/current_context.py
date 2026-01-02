# src/ui/helpers/current_context.py
"""Function(s) to Expose current runtime context"""

import streamlit as st

def require_account_id() -> str:
    account_id = st.session_state.get("account_id")
    if not account_id:
        st.info("Upload and import an XML first.")
        st.stop()
    return account_id

