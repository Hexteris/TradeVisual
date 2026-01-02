# src/io/importer.py
"""Idempotent import logic for IBKR executions."""

from typing import List, Tuple
from sqlmodel import Session, select

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

        Idempotent rules:
        - Skip if execution already exists in DB for this account (account_id, ib_execution_id).
        - Skip duplicates within the same uploaded file.
        """
        warnings: List[str] = []
        newly_inserted = 0

        # Existing exec IDs already in DB for this account
        stmt = select(Execution.ib_execution_id).where(Execution.account_id == account.id)
        rows = session.exec(stmt).all()

        # rows may come back as ["abc", "def"] OR [("abc",), ("def",)] depending on stack;
        # normalize safely.
        existing_ids = set()
        for r in rows:
            existing_ids.add(r[0] if isinstance(r, tuple) else r)

        # Also track duplicates inside this upload
        seen_in_file = set()

        for parsed in parsed_executions:
            exec_id = (parsed.ib_execution_id or "").strip()
            if not exec_id:
                warnings.append(f"Skipped execution with missing ib_execution_id: {parsed.symbol}")
                continue

            # Duplicate inside the same XML file
            if exec_id in seen_in_file:
                warnings.append(f"Skipped duplicate in file: {parsed.symbol} {exec_id}")
                continue
            seen_in_file.add(exec_id)

            # Duplicate already in DB
            if exec_id in existing_ids:
                warnings.append(f"Skipped duplicate in DB: {parsed.symbol} {exec_id}")
                continue

            execution = Execution(
                account_id=account.id,
                ib_execution_id=exec_id,
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

            # Important: update existing_ids so later rows in the same run can’t add it again
            existing_ids.add(exec_id)

        if newly_inserted:
            session.commit()

        return len(parsed_executions), newly_inserted, warnings
