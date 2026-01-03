# TradeVisual - Trading Journal

Created for traders by traders. TradeVisual provides state-of-the-art visualization which integrates seamlessly with your IBKR trading data, creating a cohesive dashboard to measure metrics and improve decision-making.

A production-ready trading journal built with Streamlit and SQLModel, inspired by Tradervue.

## Features

### IBKR Integration
- Parse IBKR Flex Query XML exports
- Automatic trade reconstruction with FIFO lot matching
- Multi-day position tracking
- Realized P&L by day

### Dashboard & Reports
- **Overview** - Win rate, profit factor, total P&L, avg win/loss
- **Equity Curve** - Cumulative P&L with drawdown analysis
- **Instrument Performance** - P&L breakdown by symbol
- **Time of Day Analysis** - Entry time performance patterns
- **Price Level Performance** - Success by stock price ranges

### Trading Journal
- **Calendar View** - Monthly P&L heatmap (green = profit, red = loss)
- **Daily Journal** - Trade breakdown with local timezone display
- **Trade List** - Advanced filtering by symbol, date, status, direction
- **CSV Export** - Download filtered trades for analysis

### Settings
- Dynamic timezone switching (US/Eastern, Asia/Singapore, etc.)
- Affects all timestamps and daily groupings
- No re-import needed

## Quick Start

### Installation

```bash
git clone https://github.com/Hexteris/TradeVisual.git
cd TradeVisual
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Running Locally

```bash
streamlit run streamlit_app.py
```

Open http://localhost:8501 in your browser.

### Usage

1. Go to **Settings** and select your preferred timezone
2. Navigate to **Import** page
3. Upload your IBKR Flex Query XML file
4. Explore your trades:
   - **Calendar** - Monthly performance overview
   - **Journal** - Daily trade details
   - **Trade List** - Filter and export trades
   - **Reports** - Comprehensive analytics

## IBKR Flex Query Setup

1. Log into IBKR Account Management
2. Go to **Reports → Flex Queries → Create**
3. Select **Trade Confirmation Flex Query**
4. Add sections: Trades, Open Positions
5. Include fields: Symbol, DateTime, Quantity, Price, Proceeds, Commission, IBOrderID
6. Save and generate XML export

## Project Structure

```
TradeVisual/
├── src/
│   ├── db/
│   │   ├── models.py          # SQLModel definitions (Trade, TradeDay, Account)
│   │   └── session.py         # SQLite in-memory database
│   ├── io/
│   │   └── ibkr_flex_parser.py # XML parsing
│   ├── domain/
│   │   ├── reconstructor.py   # FIFO trade reconstruction engine
│   │   └── metrics.py         # Analytics calculations
│   └── ui/
│       ├── app.py             # Main Streamlit app
│       ├── helpers/
│       │   └── current_context.py
│       └── pages/
│           ├── import_page.py
│           ├── calendar_page.py
│           ├── journal_page.py
│           ├── trades_list_page.py
│           └── reports_page.py
├── streamlit_app.py           # Entry point
├── requirements.txt
├── render.yaml               # Render deployment config
└── README.md
```

## Key Features Explained

### Trade Reconstruction
- **Executions** → Individual buy/sell orders from IBKR
- **Trades** → Reconstructed positions using FIFO matching
- **Trade Days** → Daily P&L breakdown (handles multi-day closes)

### FIFO Lot Matching
- Open lots tracked chronologically
- Closing executions matched to oldest lots first
- Realized P&L computed per matched lot
- Handles partial fills and position flips

### Weekend Trade Handling
Weekend executions (after-hours, settlements) automatically roll back to Friday for accurate calendar display.

### Timezone Intelligence
All timestamps converted from UTC to your selected timezone for:
- Daily trade grouping
- Calendar date assignment
- Journal and Trade List display

## Deployment

### Render.com (Recommended)

1. Push code to GitHub
2. Go to https://dashboard.render.com
3. Click **New → Web Service**
4. Connect your repository
5. Render auto-detects `render.yaml` configuration
6. Click **Create Web Service**
7. App deploys in 3-5 minutes

Your app will be live at: `https://your-app-name.onrender.com`

**Note**: Free tier spins down after inactivity. Database is session-based (data clears on restart).

## Tech Stack

- **Frontend**: Streamlit 1.52+
- **Backend**: Python 3.12
- **Database**: SQLModel + SQLite (in-memory)
- **Charts**: Plotly
- **Data Processing**: Pandas
- **XML Parsing**: lxml

## Feature Comparison

TradeVisual provides ~90% feature parity with Tradervue Silver tier ($30/month):

| Feature | TradeVisual | Tradervue Free | Tradervue Silver |
|---------|-------------|----------------|------------------|
| Trade Limit | Unlimited | 30-100/month | Unlimited |
| Calendar View | ✅ | ✅ | ✅ |
| Daily Journal | ✅ | ✅ | ✅ |
| Equity Curve | ✅ | ❌ | ✅ |
| Advanced Reports | ✅ | ❌ | ✅ |
| Filtering & Export | ✅ | ❌ | ✅ |
| Time Analysis | ✅ | ❌ | ✅ |
| Tags/Notes | ❌ | ❌ | ✅ |
| Price Charts | ❌ | ❌ | ✅ |

## Troubleshooting

**App won't start locally:**
- Check Python version: `python --version` (requires 3.12+)
- Reinstall dependencies: `pip install -r requirements.txt`

**XML import fails:**
- Ensure file is valid IBKR Flex Query XML format
- Check that all required fields are included in Flex Query
- Verify file isn't corrupted

**Timezone display issues:**
- Change timezone in Settings page
- Data updates instantly without re-import

**Calendar shows weekend trades:**
- This was fixed - weekend executions now roll back to Friday
- If still occurring, please report issue

## Future Enhancements

- [ ] Tags system (categorize trades by strategy, setup, mistakes)
- [ ] Trade notes with rich text editor
- [ ] TradingView chart integration with entry/exit markers
- [ ] Risk metrics (R-multiples, MFE/MAE)
- [ ] Performance by day of week
- [ ] Persistent database option

## License

MIT License

## Contributing

Issues and pull requests welcome! Please check existing issues before creating new ones.

---

**Built with ❤️ for the trading community**
