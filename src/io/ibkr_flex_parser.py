# src/io/ibkr_flex_parser.py
"""IBKR Flex Query XML parser."""

import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Optional, Tuple
import pytz
from dataclasses import dataclass
import re



@dataclass
class ParsedExecution:
    """Represents a single execution from IBKR Flex Query."""
    account_id: str
    ib_execution_id: str
    symbol: str
    conid: Optional[int]
    ts_raw: str
    ts_utc: datetime
    side: str  # BUY or SELL
    quantity: float
    price: float
    commission: float
    exchange: Optional[str]
    order_type: Optional[str]
    order_time_utc: Optional[datetime]
    currency: str = "USD"


class IBKRFlexParser:
    """Parse IBKR Flex Query XML exports."""
    
    IBKR_TZ = pytz.timezone("US/Eastern")
    
    @staticmethod
    def parse_timestamp(ts_str: str) -> Tuple[datetime, datetime]:
        """
        Parse IBKR timestamp with edge-case handling.

        Supported:
        - YYYYMMDD;HHMMSS
        - YYYY-MM-DD;HH:MM:SS
        - Either can optionally end with a timezone name, e.g.:
          "2025-01-02;09:31:00 US/Eastern" or "20250102;093100 America/New_York"

        Returns:
            (datetime_in_local_tz, datetime_in_utc)
        """
        ts_str = (ts_str or "").strip()
        if not ts_str:
            raise ValueError("Empty timestamp")

        # Split optional trailing tz name: "<timestamp> <TZ>"
        m = re.match(r"^(.*?)(?:\s+([A-Za-z_\/]+))?$", ts_str)
        base = m.group(1).strip()
        tz_name = (m.group(2) or "").strip()

        tz = pytz.timezone(tz_name) if tz_name else IBKRFlexParser.IBKR_TZ

        fmts = ("%Y%m%d;%H%M%S", "%Y-%m-%d;%H:%M:%S")
        last_err = None

        for fmt in fmts:
            try:
                dt_naive = datetime.strptime(base, fmt)

                # Strict DST handling:
                # - is_dst=None raises for ambiguous/non-existent times (preferred).
                try:
                    dt_local = tz.localize(dt_naive, is_dst=None)
                except (pytz.AmbiguousTimeError, pytz.NonExistentTimeError):
                    # Deterministic fallback:
                    # - For ambiguous times (clock goes back), pick standard time (is_dst=False).
                    # - For nonexistent times (clock jumps forward), also pick standard time.
                    dt_local = tz.localize(dt_naive, is_dst=False)

                return dt_local, dt_local.astimezone(pytz.UTC)

            except Exception as e:
                last_err = e

        raise ValueError(f"Unrecognized timestamp format: {ts_str}") from last_err
    
    @staticmethod
    def parse_xml(xml_content: str) -> List[ParsedExecution]:
        """Parse IBKR Flex Query XML."""
        root = ET.fromstring(xml_content)
        executions = []
        
        for trade_elem in root.findall(".//Trade"):
            try:
                account_id = trade_elem.get("accountId", "").strip()
                ib_execution_id = trade_elem.get("ibExecID", "").strip()
                symbol = trade_elem.get("symbol", "").strip()
                conid_str = trade_elem.get("conid", "")
                conid = int(conid_str) if conid_str else None

                if not account_id or not ib_execution_id or not symbol:
                    continue
                
                # Timestamp from dateTime field
                ts_raw = trade_elem.get("dateTime", "").strip()
                if not ts_raw:
                    continue
                
                _, dt_utc = IBKRFlexParser.parse_timestamp(ts_raw)

                
                side = trade_elem.get("buySell", "").strip().upper()
                if side not in ("BUY", "SELL"):
                    continue
                
                quantity = abs(float(trade_elem.get("quantity", 0)))
                price = float(trade_elem.get("tradePrice", 0))
                commission = float(trade_elem.get("ibCommission", 0))
                
                exchange = trade_elem.get("exchange", "").strip() or None
                order_type = trade_elem.get("orderType", "").strip() or None
                
                # Parse order time if present
                order_time_str = trade_elem.get("orderTime", "").strip()
                order_time_utc = None
                if order_time_str:
                    try:
                        _, order_time_utc = IBKRFlexParser.parse_timestamp(order_time_str)
                    except ValueError:
                        pass
                
                currency = "USD"  # Your XML doesn't have per-trade currency
                
                execution = ParsedExecution(
                    account_id=account_id,
                    ib_execution_id=ib_execution_id,
                    symbol=symbol,
                    conid=conid,
                    ts_raw=ts_raw,
                    ts_utc=dt_utc,
                    side=side,
                    quantity=quantity,
                    price=price,
                    commission=commission,
                    exchange=exchange,
                    order_type=order_type,
                    order_time_utc=order_time_utc,
                    currency=currency,
                )
                
                executions.append(execution)
            
            except (ValueError, AttributeError) as e:
                continue
        
        return executions
