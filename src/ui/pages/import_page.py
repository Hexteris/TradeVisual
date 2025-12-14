# src/ui/pages/import_page.py
"""Import page for uploading IBKR Flex XML."""

import streamlit as st
from sqlmodel import Session, select
import xml.etree.ElementTree as ET

from src.db.models import Account
from src.io.ibkr_flex_parser import IBKRFlexParser
from src.io.importer import IBKRImporter
from src.domain.reconstructor import TradeReconstructor


def render(session: Session):
    """Render import page."""
    st.subheader("📥 Import IBKR Flex Query")
    
    account = st.session_state.get("account")
    if not account:
        st.error("No account selected")
        return
    
    st.write(f"Importing into account: **{account.account_number}**")
    
    # File uploader
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
            
            st.info(f"Parsed {len(parsed_executions)} executions from file")
            
            # Show preview
            with st.expander("Preview Executions"):
                for exe in parsed_executions[:5]:
                    st.write(f"{exe.ts_utc} | {exe.symbol} {exe.side} {exe.quantity} @ {exe.price}")
            
            # Import button
            if st.button("Import", key="import_btn", type="primary"):
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
        
        except Exception as e:
            st.error(f"Error parsing XML: {str(e)}")
    
    # Show account statistics
    st.divider()
    st.subheader("Account Statistics")
    
    from sqlmodel import select
    from src.db.models import Execution, Trade
    
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
