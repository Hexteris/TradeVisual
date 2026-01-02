# src/ui/pages/import_page.py
"""Import page for uploading IBKR Flex XML."""

import hashlib
from uuid import uuid4

import streamlit as st
from sqlmodel import select

from src.db.session import get_session, reset_db
from src.db.models import Account, Execution, Trade
from src.io.ibkr_flex_parser import IBKRFlexParser
from src.io.importer import IBKRImporter
from src.domain.reconstructor import TradeReconstructor


def _ensure_state():
    if "uploader_key" not in st.session_state:
        st.session_state.uploader_key = str(uuid4())
    if "file_hash" not in st.session_state:
        st.session_state.file_hash = None
    if "imported_hash" not in st.session_state:
        st.session_state.imported_hash = None
    if "account_id" not in st.session_state:
        st.session_state.account_id = None


def _reset_flow():
    reset_db()
    st.session_state.file_hash = None
    st.session_state.imported_hash = None
    st.session_state.account_id = None
    st.session_state.uploader_key = str(uuid4())  # resets uploader widget
    st.rerun()


def render():
    _ensure_state()

    st.subheader("📥 Import IBKR Flex Query")

    uploaded_file = st.file_uploader(
        "Upload IBKR Flex Query XML",
        type=["xml"],
        accept_multiple_files=False,
        key=st.session_state.uploader_key,
    )

    if not uploaded_file:
        st.info("Upload an XML to begin.")
        return

    # Read bytes ONCE
    b = uploaded_file.getvalue()
    current_hash = hashlib.sha256(b).hexdigest()

    # New upload => new DB + clear analysis state
    if st.session_state.file_hash != current_hash:
        st.session_state.file_hash = current_hash
        st.session_state.imported_hash = None
        st.session_state.account_id = None
        reset_db()
        st.rerun()

    xml_content = b.decode("utf-8", errors="replace")

    parsed_executions = IBKRFlexParser.parse_xml(xml_content)
    if not parsed_executions:
        st.error("No executions found in XML")
        return

    st.caption(f"Parsed {len(parsed_executions)} executions.")

    with st.expander("Preview Executions"):
        for exe in parsed_executions[:5]:
            st.write(f"{exe.ts_utc} | {exe.symbol} {exe.side} {exe.quantity} @ {exe.price}")

    already_imported = (st.session_state.imported_hash == st.session_state.file_hash)

    col_a, col_b = st.columns([1, 1])
    with col_a:
        do_import = st.button("Import", type="primary", disabled=already_imported)
    with col_b:
        st.button("Upload another XML", on_click=_reset_flow)

    if do_import and not already_imported:
        with get_session() as session:
            # Create account if needed
            account = None
            if st.session_state.account_id:
                account = session.get(Account, st.session_state.account_id)

            if not account:
                first_exec = parsed_executions[0]
                account = Account(
                    account_number=first_exec.account_id,
                    currency=first_exec.currency,
                )
                session.add(account)
                session.commit()
                session.refresh(account)
                st.session_state.account_id = account.id

            total, new, warnings = IBKRImporter.import_executions(
                session=session,
                account=account,
                parsed_executions=parsed_executions,
            )

            if warnings:
                with st.expander("Warnings"):
                    for w in warnings[:10]:
                        st.write(f"⚠️ {w}")

            trades_created, trade_days_created = TradeReconstructor.reconstruct_for_account(
                session=session,
                account_id=account.id,
                report_timezone=st.session_state.report_timezone,

            )

        st.session_state.imported_hash = st.session_state.file_hash
        st.success(f"✅ Imported {new} new executions (processed: {total})")
        st.success(f"✅ Reconstruction: {trades_created} trades, {trade_days_created} trade days")
        st.rerun()

    # Stats (only if imported / account exists)
    if st.session_state.account_id:
        with get_session() as session:
            account = session.get(Account, st.session_state.account_id)
            if not account:
                return

            exec_count = session.exec(
                select(Execution).where(Execution.account_id == account.id)
            ).all()
            trade_count = session.exec(
                select(Trade).where(Trade.account_id == account.id)
            ).all()

        st.divider()
        st.subheader("Account Statistics")

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Executions", len(exec_count))
        col2.metric("Reconstructed Trades", len(trade_count))
        col3.metric("Open Trades", sum(1 for t in trade_count if t.status == "open"))
