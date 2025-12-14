# src/ui/app.py
"""Main Streamlit application with authentication."""

import streamlit as st
import os
from datetime import datetime
import pytz
from sqlmodel import Session, select

from src.db.session import engine, get_session, init_db
from src.db.models import User, Account, UserSetting
from src.auth import AuthManager
from src.ui.pages import import_page, journal_page, calendar_page, trades_list_page, reports_page

# Configure page
st.set_page_config(
    page_title="Trading Journal",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize database
init_db()


def init_session_state():
    """Initialize Streamlit session state."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "user" not in st.session_state:
        st.session_state.user = None
    if "account" not in st.session_state:
        st.session_state.account = None
    if "report_timezone" not in st.session_state:
        st.session_state.report_timezone = "US/Eastern"


def login_page():
    """Render login/signup page."""
    st.title("Trading Journal")
    st.write("IBKR Trade Metrics with Tradervue-like Journaling")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Login")
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        
        if st.button("Login", key="login_btn"):
            session = get_session()
            user = AuthManager.authenticate(session, username, password)
            
            if user:
                st.session_state.authenticated = True
                st.session_state.user = user
                st.success("Logged in successfully!")
                st.rerun()
            else:
                st.error("Invalid username or password")
            session.close()
    
    with col2:
        st.subheader("Sign Up")
        new_username = st.text_input("Username", key="signup_username")
        new_email = st.text_input("Email", key="signup_email")
        new_password = st.text_input("Password", type="password", key="signup_password")
        new_password_confirm = st.text_input(
            "Confirm Password", type="password", key="signup_password_confirm"
        )
        
        if st.button("Sign Up", key="signup_btn"):
            if not new_username or not new_email or not new_password:
                st.error("All fields required")
            elif new_password != new_password_confirm:
                st.error("Passwords do not match")
            else:
                session = get_session()
                result, message = AuthManager.create_user(
                    session, new_username, new_email, new_password
                )
                
                if result:
                    st.success("Account created! Please log in.")
                else:
                    st.error(message)
                session.close()


def main_app():
    """Render main application."""
    session = get_session()
    
    # Sidebar: Account selection and settings
    with st.sidebar:
        st.title("⚙️ Settings")
        
        # Load user accounts
        user = st.session_state.user
        accounts_stmt = select(Account).where(Account.user_id == user.id)
        accounts = session.exec(accounts_stmt).all()
        
        if not accounts:
            st.warning("No IBKR accounts linked. Please import trades.")
        else:
            account_names = [f"{acc.account_number} ({acc.currency})" for acc in accounts]
            selected_idx = st.selectbox(
                "Select Account",
                range(len(accounts)),
                format_func=lambda i: account_names[i],
            )
            st.session_state.account = accounts[selected_idx]
        
        # Timezone setting
        st.subheader("Report Settings")
        timezone = st.selectbox(
            "Report Timezone",
            ["US/Eastern", "US/Central", "US/Mountain", "US/Pacific", "UTC"],
            index=0,
        )
        st.session_state.report_timezone = timezone
        
        # Save setting to DB
        setting_stmt = select(UserSetting).where(
            UserSetting.user_id == user.id,
            UserSetting.key == "report_timezone",
        )
        setting = session.exec(setting_stmt).first()
        if setting:
            setting.value = timezone
        else:
            setting = UserSetting(user_id=user.id, key="report_timezone", value=timezone)
            session.add(setting)
        session.commit()
        
        st.divider()
        if st.button("Logout"):
            st.session_state.authenticated = False
            st.session_state.user = None
            st.session_state.account = None
            st.rerun()
    
    # Main navigation
    st.title("Trading Journal")

    # Always show page selector
    page = st.selectbox(
        "Navigate",
        ["Import", "Journal", "Calendar", "Trades List", "Reports"],
    )

    if page == "Import":
        import_page.render(session)
    elif st.session_state.account:
        # Other pages require an account
        if page == "Journal":
            journal_page.render(session)
        elif page == "Calendar":
            calendar_page.render(session)
        elif page == "Trades List":
            trades_list_page.render(session)
        elif page == "Reports":
            reports_page.render(session)
    else:
        st.warning("Please import trades first to create an account.")

    session.close()


if __name__ == "__main__":
    init_session_state()
    
    if st.session_state.authenticated:
        main_app()
    else:
        login_page()
