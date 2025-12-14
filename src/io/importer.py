# src/io/importer.py
"""Idempotent import logic for IBKR executions."""

from typing import List, Dict, Tuple
from sqlmodel import Session, select
from datetime import datetime
import pytz

from src.db.models import Execution, Account
from src.io.ibkr_flex_parser import ParsedExecution


class IBKRImporter:
    """Handles idempotent import of executions."""
    
    @staticmethod
    def import_executions(
        session: Session,
        account: Account,
        parsed_executions: List[ParsedExecution],
    ) -> Tuple[int, int, List[str]]:
        """
        Import parsed executions into database.
        Idempotent: duplicate (account_id, ib_execution_id) are skipped.
        
        Args:
            session: SQLModel session
            account: Account to import into
            parsed_executions: List of ParsedExecution objects
        
        Returns:
            (total_processed, newly_inserted, warnings)
        """
        warnings = []
        newly_inserted = 0
        
        # Get existing execution IDs for this account
        existing_stmt = select(Execution.ib_execution_id).where(
            Execution.account_id == account.id
        )
        existing_ids = {row[0] for row in session.exec(existing_stmt).all()}
        
        for parsed in parsed_executions:
            # Idempotency check
            if parsed.ib_execution_id in existing_ids:
                warnings.append(
                    f"Skipped duplicate execution: {parsed.symbol} {parsed.ib_execution_id}"
                )
                continue
            
            # Create new execution
            execution = Execution(
                account_id=account.id,
                ib_execution_id=parsed.ib_execution_id,
                symbol=parsed.symbol,
                conid=parsed.conid,
                ts_utc=parsed.ts_utc,
                ts_raw=parsed.ts_raw,
                side=parsed.side,
                quantity=parsed.quantity,
                price=parsed.price,
                commission=parsed.commission,
                exchange=parsed.exchange,
                order_type=parsed.order_type,
                order_time_utc=parsed.order_time_utc,
                currency=parsed.currency,
            )
            
            session.add(execution)
            newly_inserted += 1
        
        # Commit all new executions
        if newly_inserted > 0:
            session.commit()
        
        return len(parsed_executions), newly_inserted, warnings
