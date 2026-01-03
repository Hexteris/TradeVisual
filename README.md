# TradeVisual - Trading Journal (Using IBKR Flex XML)

Created for traders by traders. TradeVisual provides state of the art visualisation which integrates seemlessly with your trading data, creating a cohesive dashboard for users to measure their metrics and improve decision making during trading sessions. TradeVisual is built with Streamlit and SQLModel that imports Interactive Brokers (IBKR) Flex Query XML, reconstructs trades via FIFO lot matching, and visualizes performance via a calendar, journal, and reports.

Live demo: https://tradevisual.onrender.com/

> Note: This app uses an in-memory SQLite database (session-based). Your data resets when the app restarts (e.g., Render free tier spin-down).

---

## Features

### IBKR integration
- Import IBKR Flex Query **XML** (Trade Confirmation Flex Query).
- Parse executions (fills) into a normalized execution model.
- Automatic trade reconstruction using FIFO lot matching.
- Multi-day position tracking and realized P&L by day.
- Weekend handling: executions falling on Saturday/Sunday are rolled back to Friday for calendar grouping.

### Dashboard & reports
- Overview: win rate, profit factor, total P&L, avg win/loss.
- Equity curve: cumulative P&L + drawdown + daily P&L.
- Instrument performance: P&L by symbol.
- Time-of-day analysis: entry-time performance patterns.
- Price level performance: success by stock price ranges.

### Trading journal
- Calendar view: monthly P&L heatmap.
- Daily journal: per-day breakdown with local timezone display.
- Trades list: filtering by symbol/date/status/direction.
- CSV export: download filtered trades.

### Settings
- Dynamic timezone switching (US/Eastern, Asia/Singapore, etc.).
- Timezone impacts timestamps and daily groupings without re-import.

---

## Quick start

### Prerequisites
- Python 3.12+

### Installation
```bash
git clone https://github.com/Hexteris/TradeVisual.git
cd TradeVisual

python -m venv venv
# macOS/Linux:
source venv/bin/activate
# Windows (PowerShell):
venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

### Run locally
```bash
streamlit run streamlit_app.py
```

Open http://localhost:8501

---

## How to use

1. Open **Settings** and select your preferred timezone.
2. Go to the **Import** page.
3. Upload your IBKR Flex Query `.xml`.
4. Explore:
   - **Calendar** (monthly performance)
   - **Journal** (daily breakdown)
   - **Trade List** (filter + export)
   - **Reports** (analytics)

---

## Getting the IBKR `.xml` (Flex Query)

TradeVisual expects an IBKR **Flex Query export** in **XML** format.

### Create a Trade Confirmation Flex Query (template)
1. Log in to the IBKR Client Portal.
2. Go to **Performance & Reports → Flex Queries**.
3. Create a new **Trade Confirmation Flex Query** template.
4. Set output format to **XML**.

### Include required fields
When selecting fields for the Trades/Confirmations section, ensure your XML includes at least:
- `accountId`
- `ibExecID`
- `symbol` (and optionally `conid`)
- `dateTime`
- `buySell`
- `quantity`
- `tradePrice`
- `ibCommission`

Optional (nice-to-have):
- `exchange`
- `orderType`
- `orderTime`

### Date/time formatting (must match parser)
The parser accepts:
- `YYYYMMDD;HHMMSS` (example: `20250102;093100`)
- `YYYY-MM-DD;HH:MM:SS` (example: `2025-01-02;09:31:00`)
- Either format may optionally include a trailing timezone name (example: `2025-01-02;09:31:00 US/Eastern`)

### Run the query and download XML
1. From the Flex Queries page, run the saved query.
2. Download the generated report (IBKR may provide an XML file or a zipped download depending on settings).
3. Upload the `.xml` file into TradeVisual on the **Import** page.

---

## Tests

Run:
```bash
pytest -x -vv
```

What’s covered:
- Parser smoke test: XML → parsed executions > 0
- Metrics smoke test: equity curve computation returns non-empty
- FIFO correctness test: deterministic 3-fill scenario verifies FIFO realized gross/net P&L via the reconstructor and SQLModel

---

## Project structure

```text
TradeVisual/
├── src/
│   ├── db/
│   │   ├── models.py            # SQLModel definitions (Account, Execution, Trade, TradeDay)
│   │   └── session.py           # Session-only SQLite (in-memory)
│   ├── io/
│   │   └── ibkr_flex_parser.py  # IBKR Flex XML parsing
│   ├── domain/
│   │   ├── reconstructor.py     # FIFO trade reconstruction engine
│   │   └── metrics.py           # Analytics calculations
│   └── ui/
│       ├── app.py               # Main Streamlit app
│       ├── helpers/
│       │   └── current_context.py
│       └── pages/
│           ├── import_page.py
│           ├── calendar_page.py
│           ├── journal_page.py
│           ├── trades_list_page.py
│           └── reports_page.py
├── streamlit_app.py             # Streamlit entry point
├── requirements.txt
├── render.yaml                   # Render deployment config
└── README.md
```

---

## Deployment (Render)

1. Push code to GitHub.
2. Create a new Render **Web Service** and connect the repository.
3. Ensure the start command runs Streamlit from the repo root:
   ```bash
   streamlit run streamlit_app.py
   ```
4. Deploy.

Free tier note: services can spin down after inactivity, and in-memory data will reset on restart.

---

## Troubleshooting

### App won’t start locally
- Verify Python: `python --version` (3.12+ recommended).
- Reinstall deps: `pip install -r requirements.txt`.

### XML import fails
- Confirm the file is an IBKR Flex Query XML export (Trade Confirmation Flex Query).
- Confirm the XML contains the required fields listed above.
- Confirm `dateTime` matches one of the supported formats.

### Timezone display issues
- Change timezone in **Settings**.
- Views update immediately; no re-import required.

---

## License
MIT

## Contributing
Issues and pull requests are welcome.

## Disclaimer
TradeVisual is for educational/analysis purposes and is not financial advice.
```

What IBKR UI are you currently using to export the report: the **Client Portal** (web) or **Account Management / Reports** menus (older wording), and does IBKR give you a plain `.xml` or a `.zip` download most of the time?

[1](https://www.ibkrguides.com/complianceportal/runaflexquery.htm)