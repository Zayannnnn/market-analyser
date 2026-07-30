# Apex Stock Intelligence Engine: Developer Guide

This guide helps developers modify, debug, and extend the AORA platform.

---

## 1. Extending Data Sources

### 1.1 Adding a New Stock Data Provider
Currently, live quotes and historical candles are resolved in `backend/app/data_sources/market_data.py`. To plug in an alternative provider (e.g. Zerodha Kite, Angel One SmartAPI, Yahoo Finance):

1. **Implement Fetch Method**: Create a new file or add a function in `market_data.py` adhering to this signature:
   ```python
   def get_alternate_market_data(symbol: str) -> dict:
       # Implement REST api calls to retrieve current price, yesterday close, and candles
       return {
           "price": float_price,
           "change": price_change,
           "history_close": list_of_closes
       }
   ```
2. **Inject into Technical Agent**: Open `backend/app/agents/technical.py` and replace the default `get_market_data` import with your custom provider.
3. **Register Fallbacks**: Update exception handlers inside `technical.py` to fallback to default providers if your custom service goes offline.

### 1.2 Adding a New News RSS Source
News scraping is managed by the Scraping agent inside `backend/app/data_sources/rss_scrapers.py`.
1. Open `rss_scrapers.py`.
2. Locate the static feeds list:
   ```python
   FEEDS = [
       "https://news.google.com/rss/search?q={term}&hl=en-IN&gl=IN&ceid=IN:en",
       # Add your new XML feed here
   ]
   ```
3. Ensure the XML structure is parsed correctly by `feedparser`. Add mapping rules if fields like `published` use non-standard keys.

---

## 2. Pluggable AI Models

To replace or combine Gemini 2.5 Flash with alternative models (e.g. Claude 3.5 Sonnet, OpenAI GPT-4o):

1. **Create Client Class**: In `backend/app/utils.py` or a dedicated wrapper, initialize the alternative API client.
2. **Implement Completion Handler**:
   ```python
   def generate_ai_completion(prompt: str) -> str:
       # Implement API client call and return plain text response
       pass
   ```
3. **Refactor Prompts Callers**: Open `backend/app/agents/sentiment.py`, `backend/app/agents/explanation.py`, and `backend/app/services/ai_trade_review.py`. Replace calls to `genai.GenerativeModel` with your custom completion handler.

---

## 3. Extending the Risk Engine

The Risk Engine resides in `backend/app/services/risk_engine.py`. To add custom rules (e.g. max trades per day, minimum liquidity check):

1. **Add Rule Parameter**: Open the risk configuration model and Firestore database schema. Add your parameter, e.g. `max_daily_trades: int`.
2. **Implement Rule Check**: Open `risk_engine.py` and add a validator method:
   ```python
   def check_daily_trades_limit(db, max_trades: int) -> bool:
       # Read today's executed trades from Firestore paper_trades / live_trades
       # Return False if count >= max_trades
       pass
   ```
3. **Inject into Safety Pipe**: Call the validator inside the `validate_portfolio_risk_rules` check.

---

## 4. Debugging & Deployment

### 4.1 Running Local Tests
To check for syntax errors, mock state issues, and endpoint availability, run:
```bash
# Verify auth notification throttling and cooldowns
.\backend\venv\Scripts\python.exe -m unittest backend/test_auth_notifications.py

# Verify risk engine exposure limits
.\backend\venv\Scripts\python.exe -m unittest backend/test_portfolio_manager.py

# Verify Upstox mock trading
.\backend\venv\Scripts\python.exe -m unittest backend/test_trading.py
```

### 4.2 Firebase functions Deployment
AORA uses standard Firebase Functions decorated with `@https_fn.on_request` in `backend/main.py`.
```bash
# Deploy only backend cloud functions
firebase deploy --only functions

# Deploy complete resources
firebase deploy --only hosting,functions
```
Ensure you have run `npm run build` in the `frontend` folder to compile your React bundle before deploying hosting!
