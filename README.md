# README.md
# Trading Journal - IBKR Edition

# TradeVisual
Created for trader by traders. TradeVisual provides state of the art visualisation which integrates seemlessly with your trading data, creating a cohesive dashboard for users to measure their metrics and improve decision making during trading sessions. 
A production-ready Tradervue-like trading journal built with Streamlit, SQLModel, and IBKR Flex Query exports.

## Features

**IBKR Integration**
- Parse IBKR Flex Query XML exports (idempotent)
- Support for multiple accounts
- Comprehensive execution data capture

**Trade Reconstruction**
- Deterministic FIFO lot matching
- Partial fills and position tracking
- Handle flips and multi-day trades
- Realized P&L by day

**Reporting**
- Daily journal with P&L by day
- Monthly calendar heatmap
- Equity curve with drawdown
- Trade list with filters
- Performance by instrument

**Authentication**
- User sign-up/login
- Secure password hashing (bcrypt)
- Multi-user support

**Multi-Database Support**
- SQLite for local development
- PostgreSQL (Neon) for production

## Quick Start

### Local Development

1. **Clone and install:**
   ```bash
   git clone <repo>
   cd trading-journal
   pip install -r requirements.txt
   ```

2. **Configure database:**
   ```bash
   cp .env.example .env
   # .env defaults to SQLite (trading_journal.db)
   ```

3. **Run app:**
   ```bash
   streamlit run src/ui/app.py
   ```

4. **Create account:**
   - Use signup form on first load
   - Upload your `Trade_Metrics.xml` (IBKR Flex export)

### Production (Render + Neon)

1. **Create Neon PostgreSQL database:**
   - Get connection string: `postgresql+psycopg2://user:password@ep-xxx.neon.tech/dbname`

2. **Deploy to Render:**
   ```bash
   git push origin main
   ```

3. **Set environment variable on Render:**
   ```
   DATABASE_URL=postgresql+psycopg2://...
   ```

## Project Structure

```
trading-journal/
├── src/
│   ├── db/
│   │   ├── models.py          # SQLModel definitions
│   │   └── session.py         # DB connection factory
│   ├── io/
│   │   ├── ibkr_flex_parser.py # XML parsing
│   │   └── importer.py        # Idempotent import
│   ├── domain/
│   │   ├── reconstructor.py   # Trade reconstruction engine
│   │   ├── models.py          # Domain models
│   │   └── metrics.py         # Calculation engine
│   ├── ui/
│   │   ├── app.py             # Main Streamlit app
│   │   └── pages/
│   │       ├── import_page.py
│   │       ├── journal_page.py
│   │       ├── calendar_page.py
│   │       ├── trades_list_page.py
│   │       └── reports_page.py
│   └── auth.py                # Authentication
├── tests/
│   ├── test_parser.py
│   ├── test_reconstructor.py
│   └── test_metrics.py
├── requirements.txt
└── README.md
```

## Usage

### Importing Trades

1. Go to **Import** page
2. Upload your IBKR Flex Query XML (`Trade_Metrics.xml`)
3. Preview and click **Import**
4. Trades are reconstructed automatically

### Viewing Trades

- **Journal**: Daily P&L breakdown
- **Calendar**: Monthly heatmap (green = profit, red = loss)
- **Trades List**: Filterable table of all trades
- **Reports**: Overview stats, instrument performance, equity curve

### Settings

- **Report Timezone**: Change day boundaries (default: US/Eastern)
- Persisted in database

## Key Concepts

### Trade Reconstruction
- **Executions** → individual buy/sell orders from IBKR
- **Trades** → reconstructed positions (may span multiple executions)
- **Trade Days** → daily P&L broken down (handles multi-day closes)

### FIFO Lot Matching
- Open lots tracked in order
- Closing execution matched to oldest lots first
- Realized P&L computed per matched lot

### Realized P&L by Day
Unlike some tools, P&L is attributed to the day the transaction occurred (not settlement), enabling accurate daily tracking of swing trades.

## Testing

```bash
pytest tests/ -v
```

Tests cover:
- XML parsing and idempotency
- FIFO lot matching
- Trade reconstruction edge cases
- Timezone handling

## Data Schema

### Execution
Individual trade execution from IBKR. Keyed by (account_id, ib_execution_id).

### Trade
Reconstructed position. Spans one or more executions. Has lifecycle (open → closed).

### TradeDay
Daily summary for a trade. Handles multi-day partial closes.

### Tag
User-defined label for trades (future: filtering/grouping).

## Limitations & Future Work

- **No MFE/MAE**: Requires intraday candle data integration
- **No split/merge UI**: Backend schema ready, UI deferred
- **No time-of-day reporting**: Can add hour-of-day bucketing
- **SQLite → Neon**: Binary data format differs slightly; full Neon testing pending

## Configuration

### Environment Variables

- `DATABASE_URL`: Database connection string
  - Local: `sqlite:///./trading_journal.db`
  - Neon: `postgresql+psycopg2://user:pass@host/db`

### Timezone Support

Report timezone is configurable in settings. Affects:
- Day boundaries for trade_day grouping
- Calendar heatmap dates
- Journal view

## Troubleshooting

**"No account selected"**
- Import an IBKR XML file first (creates default account from XML)

**Trades not showing after import**
- Check import page for parsing warnings
- Ensure XML is valid IBKR Flex Query export

**Duplicate executions**
- Re-importing same file is safe (idempotent by design)

## License

MIT

---

## Support

For questions or issues:
1. Check README troubleshooting
2. Review test files for examples
3. Check database schema in `src/db/models.py`
