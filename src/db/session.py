# src/db/session.py
"""Per-session in-memory DB for Streamlit (no persistence)."""

import streamlit as st
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine

_ENGINE_KEY = "db_engine"


def _new_engine():
    return create_engine(
        "sqlite://",  # in-memory
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # keep one connection; DB survives while engine exists
        echo=False,
    )


def reset_db():
    """Forget the current in-memory DB; next get_session() recreates it."""
    st.session_state.pop(_ENGINE_KEY, None)


def get_engine():
    """Get/create the engine for this browser tab."""
    if _ENGINE_KEY not in st.session_state:
        st.session_state[_ENGINE_KEY] = _new_engine()
        SQLModel.metadata.create_all(st.session_state[_ENGINE_KEY])
    return st.session_state[_ENGINE_KEY]


def get_session() -> Session:
    """Get a SQLModel session bound to this tab's in-memory DB."""
    return Session(get_engine())
