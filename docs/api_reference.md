# Apex Stock Intelligence Engine: API Reference

This document provides a detailed catalog of the FastAPI REST API endpoints exposed by the AORA backend.

---

## 1. Global Endpoints

### 1.1 Root Status
* **Method**: `GET`
* **URL**: `/`
* **Response**:
  ```json
  {
    "status": "online",
    "timestamp": "2026-07-31T00:30:00Z",
    "engine": "Apex Stock Intelligence Engine"
  }
  ```
* **Purpose**: General status check to verify server availability.

---

## 2. Dashboard & Leaderboard Feed

### 2.1 Dynamic Top 10 Leaderboard
* **Method**: `GET`
* **URL**: `/api/top10`
* **Query Parameters**: None
* **Caching**: Internal memory-cache for 15 minutes (`cache_expiry_seconds` configuration).
* **Response**:
  ```json
  {
    "timestamp": "2026-07-31T00:30:00Z",
    "top_10": [
      {
        "ticker": "TCS",
        "company_name": "Tata Consultancy Services Ltd.",
        "score": 8.75,
        "price": 3850.50,
        "change_pct": 1.25,
        "technical_signals": {
          "rsi": 62.4,
          "macd": "bullish",
          "trend": "bullish"
        },
        "ai_explanation": "Strong earnings momentum coupled with break out of a key resistance channel.",
        "news_impact": 0.85
      }
    ]
  }
  ```
* **Flow**:
  1. Checks local cache for `"top10"` key.
  2. If cache miss, reads the `rankings/current` document in Firestore.
  3. If database rankings document doesn't exist, runs a synchronous pipeline execution, writes the result to database, updates cache, and returns rankings.

### 2.2 Market Summary Telemetry
* **Method**: `GET`
* **URL**: `/api/market-summary`
* **Response**: Contains status dials for Nifty 50, Nifty Bank, overall market regime, sector momentum list, and current pipeline health signals.

---

## 3. Stock Detail & Fundamental Research

### 3.1 Single Stock Summary
* **Method**: `GET`
* **URL**: `/api/stocks/{ticker}`
* **Parameters**: `ticker` (string, path parameter, required)
* **Response**: Returns technical metrics, historical candle plots data, cataloged news, and stored AI recommendations.

### 3.2 Fundamental Valuation & Catalyst Research
* **Method**: `GET`
* **URL**: `/api/stocks/{ticker}/research`
* **Parameters**: `ticker` (string, path parameter, required)
* **Response**:
  ```json
  {
    "status": "success",
    "research": {
      "ticker": "TCS",
      "fundamental_score": 88,
      "intrinsic_value": 4120.00,
      "margin_of_safety": 6.5,
      "catalysts": [
        {"date": "2026-08-15", "event": "Quarterly Earnings Announcement"}
      ],
      "ai_equity_memo": "TCS demonstrates stable free cash flow generation with premium operating margins..."
    }
  }
  ```
* **Flow**: Fetches fundamentals from Firestore `research/` collection. If stale or missing, automatically triggers a fresh live fundamental compiler, stores the report, and returns the insights.

---

## 4. Upstox OAuth Authentication

### 4.1 Connection Status
* **Method**: `GET`
* **URL**: `/api/upstox/auth-status`
* **Response**: Returns Dynamic Upstox connection state (`CONNECTED`, `EXPIRED`, `CONNECTING`, `ERROR`), token age, token expected expiry, and public login URL callback.

### 4.2 OAuth Redirection Initiation
* **Method**: `GET`
* **URL**: `/api/upstox/login`
* **Query Parameters**: `force` (boolean, optional, default: `false`)
* **Flow**: Generates the redirect URL pointing to the broker's login page. If `force=false` and a valid session is active, redirects straight to the frontend dashboard.

### 4.3 OAuth Authorization Code Callback
* **Method**: `GET`
* **URL**: `/api/upstox/callback`
* **Query Parameters**: `code` (string, path parameter, required)
* **Flow**:
  1. Checks if the authorization code was already processed.
  2. Exchanges code for access token via Upstox REST endpoint.
  3. Verifies token E2E by hitting user profile, long-term holdings, and funds endpoints.
  4. Saves token inside Firestore documents `config/upstox` and `config/upstox_auth`.
  5. Updates `config/runtime_state` to set `upstox_connected = True` and `expiry_notification_sent = False`.
  6. Resumes live trading by setting `live_trading_enabled = True` in `/live_trading/config`.
  7. Dispatches a successful connection alert to Telegram and redirects the user back to the web dashboard.

---

## 5. Live Trading Operations

### 5.1 Execute Trade Suggestion
* **Method**: `POST`
* **URL**: `/api/trading/buy` or `/api/trading/sell`
* **Body Model**:
  ```json
  {
    "ticker": "INFY",
    "quantity": 10,
    "price": 1420.00,
    "transaction_type": "BUY"
  }
  ```
* **Flow**: Validates details against the **Risk Engine**. Checks single stock exposure weight, sector cap breaches, daily losses, and buying power. If passed, triggers direct Upstox execution or enters confirming state depending on the active execution mode.

### 5.2 Approve Pending Suggestion Callback
* **Method**: `GET`
* **URL**: `/api/live/approve`
* **Query Parameters**: `order_id` (string, path parameter, required)
* **Flow**: Manual callback trigger (usually clicked from a Telegram alert button). Validates order state in Firestore, requests execution on Upstox, updates order status, and notifies the user of the trade confirmation.
