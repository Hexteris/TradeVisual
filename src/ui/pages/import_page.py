# src/ui/pages/import_page.py
"""Import page for uploading IBKR Flex XML."""

import streamlit as st
from sqlmodel import Session, select
import xml.etree.ElementTree as ET

from src.db.models import Account, Execution, Trade
from src.io.ibkr_flex_parser import IBKRFlexParser
from src.io.importer import IBKRImporter
from src.domain.reconstructor import TradeReconstructor


def render(session: Session):
    """Render import page."""
    st.subheader("📥 Import IBKR Flex Query")
    
    user = st.session_state.get("user")
    account = st.session_state.get("account")
    
    if account:
        st.write(f"Importing into account: **{account.account_number}**")
    else:
        st.info("No account yet. Upload your first XML file to create one.")
    
    # File uploader (always show)
    uploaded_file = st.file_uploader(
        "Upload IBKR Flex Query XML",
        type=["xml"],
        accept_multiple_files=False,
    )
    
    if uploaded_file:
        try:
            xml_content = uploaded_file.read().decode('utf-8')
            
            # Parse XML
            parsed_executions = IBKRFlexParser.parse_xml(xml_content)
            
            if not parsed_executions:
                st.error("No executions found in XML")
                return
            
            st.info(f"Parsed {len(parsed_executions)} executions from file")
            
            # Show preview
            with st.expander("Preview Executions"):
                for exe in parsed_executions[:5]:
                    st.write(f"{exe.ts_utc} | {exe.symbol} {exe.side} {exe.quantity} @ {exe.price}")
            
            # Import button
            if st.button("Import", key="import_btn", type="primary"):
                # If no account exists, create one from the first execution
                if not account:
                    first_exec = parsed_executions[0]
                    account = Account(
                        user_id=user.id,
                        account_number=first_exec.account_id,
                        currency=first_exec.currency,
                    )
                    session.add(account)
                    session.commit()
                    session.refresh(account)
                    st.session_state.account = account
                    st.success(f"✅ Created account: {account.account_number}")
                
                # Import executions
                total, new, warnings = IBKRImporter.import_executions(
                    session=session,
                    account=account,
                    parsed_executions=parsed_executions,
                )
                
                st.success(f"✅ Imported {new} new executions (total processed: {total})")
                
                if warnings:
                    with st.expander("Warnings"):
                        for w in warnings[:10]:
                            st.write(f"⚠️ {w}")
                
                # Reconstruct trades
                st.info("Reconstructing trades...")
                trades_created, trade_days_created = TradeReconstructor.reconstruct_for_account(
                    session=session,
                    account_id=account.id,
                    report_timezone=st.session_state.get("report_timezone", "US/Eastern"),
                )
                
                st.success(
                    f"✅ Trade reconstruction complete: {trades_created} trades, {trade_days_created} trade days"
                )
                
                st.info("🔄 Refreshing page...")
                st.rerun()
        
        except Exception as e:
            st.error(f"Error: {str(e)}")
            import traceback
            st.code(traceback.format_exc())
    
    # Show account statistics (only if account exists)
    if account:
        st.divider()
        st.subheader("Account Statistics")
        
        exec_count = session.exec(
            select(Execution).where(Execution.account_id == account.id)
        ).all()
        trade_count = session.exec(
            select(Trade).where(Trade.account_id == account.id)
        ).all()
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Executions", len(exec_count))
        col2.metric("Reconstructed Trades", len(trade_count))
        col3.metric("Open Trades", len([t for t in trade_count if t.status == "open"]))

