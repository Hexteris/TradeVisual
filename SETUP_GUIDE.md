# SETUP_GUIDE.md
# Complete Setup Guide

## Prerequisites

- Python 3.9+
- Git
- IBKR account with Flex Query access
- (Production) Render account + Neon database

## Local Development Setup

### 1. Clone Repository

```bash
git clone <repo-url>
cd trading-journal
```

### 2. Create Virtual Environment

```bash
python -m venv venv

# On Windows:
venv\Scripts\activate

# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Environment Variables

```bash
cp .env.example .env
```

By default, `.env` uses SQLite. No further configuration needed for local testing.

### 5. Run Application

```bash
streamlit run src/ui/app.py
```

The app will open at `http://localhost:8501`

### 6. Create Account

1. Click **Sign Up**
2. Enter username, email, password
3. Click **Sign Up**
4. Go back and **Login**

### 7. Import Your First Trade

1. Navigate to **Import** page
2. Click **Upload IBKR Flex Query XML**
3. Select your `Trade_Metrics.xml` file
4. Preview the parsed executions
5. Click **Import**
6. Wait for trade reconstruction

### 8. Explore Data

- **Journal**: Click a date to see daily P&L
- **Calendar**: View monthly heatmap
- **Trades List**: See all reconstructed trades
- **Reports**: View statistics and equity curve

---

## Production Deployment (Render + Neon)

### 1. Create Neon Database

1. Go to [https://console.neon.tech](https://console.neon.tech)
2. Sign up / Log in
3. Create new project (e.g., "trading-journal")
4. Copy connection string:
   ```
   postgresql+psycopg2://user:password@ep-xxx.neon.tech/trading-journal
   ```

### 2. Push to GitHub

```bash
git init
git add .
git commit -m "Initial commit: trading journal MVP"
git branch -M main
git remote add origin https://github.com/username/trading-journal.git
git push -u origin main
```

### 3. Create Render Deployment

1. Go to [https://render.com](https://render.com)
2. Click **New** → **Web Service**
3. Connect GitHub repository
4. Configure:
   - **Name**: trading-journal
   - **Runtime**: Python 3.9
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `streamlit run src/ui/app.py`

### 4. Set Environment Variables on Render

In Render dashboard for your service:

1. Go to **Environment**
2. Add:
   - **Key**: `DATABASE_URL`
   - **Value**: `postgresql+psycopg2://user:password@ep-xxx.neon.tech/trading-journal`

3. Also add (Streamlit-specific):
   - **Key**: `STREAMLIT_SERVER_PORT`
   - **Value**: `10000`
   - **Key**: `STREAMLIT_SERVER_ADDRESS`
   - **Value**: `0.0.0.0`
   - **Key**: `STREAMLIT_SERVER_HEADLESS`
   - **Value**: `true`

### 5. Deploy

Click **Deploy** and wait ~5-10 minutes. Once done, your app is live!

---

## File Structure

After setup, you should have:

```
trading-journal/
├── src/
│   ├── db/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   └── session.py
│   ├── io/
│   │   ├── __init__.py
│   │   ├── ibkr_flex_parser.py
│   │   └── importer.py
│   ├── domain/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── reconstructor.py
│   │   └── metrics.py
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── app.py
│   │   └── pages/
│   │       ├── __init__.py
│   │       ├── import_page.py
│   │       ├── journal_page.py
│   │       ├── calendar_page.py
│   │       ├── trades_list_page.py
│   │       └── reports_page.py
│   └── auth.py
├── tests/
│   ├── conftest.py
│   ├── test_parser.py
│   ├── test_reconstructor.py
│   └── test_metrics.py
├── .env
├── .env.example
├── .gitignore
├── requirements.txt
├── README.md
└── SETUP_GUIDE.md
```

---

## IBKR Flex Query Setup

### Getting Your Trade_Metrics.xml

1. Log into IBKR Account Management
2. Go to **Reports** → **Flex Queries** → **My Queries**
3. Create new query or use existing
4. Set date range (e.g., all time)
5. Ensure these fields are selected:
   - `accountId`
   - `tradeID` (execution ID)
   - `symbol`
   - `conid`
   - `tradeTime`
   - `buySell`
   - `quantity`
   - `tradePrice`
   - `ibCommission`
   - `exchange`
   - `orderType`
   - `orderTime`
6. Click **Run** and download XML
7. Save as `Trade_Metrics.xml`

---

## Troubleshooting

### "ImportError: No module named 'src'"

Make sure you're running from the project root:
```bash
cd /path/to/trading-journal
streamlit run src/ui/app.py
```

### "No account selected" in UI

1. Go to **Import** page
2. Upload your IBKR XML file
3. Click **Import**
4. This creates your account

### "Database is locked" (SQLite)

If using SQLite and seeing lock errors:
- Close the app
- Delete `trading_journal.db`
- Restart app
- Re-import data

### Neon Connection Errors

1. Verify `DATABASE_URL` format: `postgresql+psycopg2://user:pass@host/db`
2. Check Neon dashboard for active connection
3. Ensure credentials are correct (no typos)

### Port Already in Use (Local)

```bash
streamlit run src/ui/app.py --server.port 8502
```

---

## Data Backup

### SQLite Backup (Local)

```bash
cp trading_journal.db trading_journal.db.backup
```

### Neon Backup (Production)

Neon automatically maintains backups. You can also:
1. Export data via SQL: `pg_dump` connection
2. Or use Neon's built-in backup features

---

## Next Steps

Once running:

1. **Explore your trades** in the Journal and Calendar
2. **Check Reports** for overview metrics
3. **Verify P&L accuracy** against IBKR
4. **(v2) Add tagging** to classify trades
5. **(v2) Implement split/merge** for trade adjustments
6. **(v3) Integrate candles** for MFE/MAE calculation

---

## Support

For issues:
1. Check README.md troubleshooting
2. Review test files: `tests/`
3. Check database schema: `src/db/models.py`
4. Enable Streamlit debug: `streamlit run ... --logger.level=debug`
