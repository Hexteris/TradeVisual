# src/io/ibkr_flex_parser.py
"""
IBKR Flex Query XML parser.
Handles parsing, normalization, and idempotent storage.
"""

import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import pytz
from dataclasses import dataclass


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
    
    # Common IBKR timestamp formats
    TIMESTAMP_FORMATS = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d, %H:%M:%S",
        "%Y%m%d %H:%M:%S",
    ]
    
    # Assume IBKR timestamps are in US/Eastern (trading hours reference)
    IBKR_TZ = pytz.timezone("US/Eastern")
    
    @staticmethod
    def parse_timestamp(ts_str: str) -> Tuple[datetime, datetime]:
        """
        Parse IBKR timestamp string to (aware_local, utc).
        
        Args:
            ts_str: Timestamp string from IBKR (e.g., "2025-01-15 09:30:00")
        
        Returns:
            (datetime_in_et, datetime_in_utc)
        """
        dt_naive = None
        
        for fmt in IBKRFlexParser.TIMESTAMP_FORMATS:
            try:
                dt_naive = datetime.strptime(ts_str, fmt)
                break
            except ValueError:
                continue
        
        if dt_naive is None:
            raise ValueError(f"Could not parse timestamp: {ts_str}")
        
        # Assume IBKR timestamps are in US/Eastern
        dt_et = IBKRFlexParser.IBKR_TZ.localize(dt_naive)
        dt_utc = dt_et.astimezone(pytz.UTC)
        
        return dt_et, dt_utc
    
    @staticmethod
    def parse_xml(xml_content: str) -> List[ParsedExecution]:
        """
        Parse IBKR Flex Query XML.
        
        Args:
            xml_content: Raw XML string from IBKR
        
        Returns:
            List of ParsedExecution objects
        """
        root = ET.fromstring(xml_content)
        executions = []
        
        # Navigate: FlexQueryResponse -> FlexStatements -> FlexStatement -> Trades -> Trade
        for trade_elem in root.findall(".//Trade"):
            try:
                account_id = trade_elem.get("accountId", "").strip()
                ib_execution_id = trade_elem.get("tradeID", "").strip()
                symbol = trade_elem.get("symbol", "").strip()
                conid_str = trade_elem.get("conid", "")
                conid = int(conid_str) if conid_str else None
                
                # Timestamp: use tradeTime (actual execution)
                ts_raw = trade_elem.get("tradeTime", "").strip()
                if not ts_raw:
                    # Fallback to orderTime if tradeTime missing
                    ts_raw = trade_elem.get("orderTime", "").strip()
                
                if not ts_raw:
                    continue  # Skip if no timestamp
                
                dt_et, dt_utc = IBKRFlexParser.parse_timestamp(ts_raw)
                
                side = trade_elem.get("buySell", "").strip().upper()
                if side not in ("BUY", "SELL"):
                    continue
                
                quantity = float(trade_elem.get("quantity", 0))
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
                
                currency = trade_elem.get("currency", "USD").strip() or "USD"
                
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
                # Log and skip malformed records
                continue
        
        return executions
