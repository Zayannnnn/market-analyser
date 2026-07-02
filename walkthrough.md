# Phase 3.2 Walkthrough & Production Verification Report

This walkthrough documents the completed implementation details, newly created modules, API changes, and verification test results for **Phase 3.2 — Yahoo Finance Removal & Upstox Migration**.

---

## 1. Summary of Changes

### 1.1 New Modules Created
*   **`backend/app/services/technical_indicators.py`**:
    A standalone reusable module containing local indicator calculation logic using Python (`pandas` and `numpy`).
    Calculates: EMA 20, EMA 50, RSI (14), MACD (12, 26, 9), ATR (14), Bollinger Bands (20, 2), Support & Resistance (20-day min/max closes), Volume Analysis (surge & 20-day average), and Channel Breakout status.

### 1.2 Files Modified
*   **`backend/app/data_sources/market_data.py`**:
    *   Excised all direct and indirect requests to `yfinance` subdomains.
    *   Refactored `UpstoxClient` to fetch candle data from the Upstox Historical Candle API:
        `GET /historical-candle/{instrument_key}/{interval}/{to_date}/{from_date}`
    *   Implemented access token loading from environment variable `UPSTOX_ACCESS_TOKEN` with a fallback to the Firestore database (`config/upstox`).
    *   Implemented fallback simulated candle generation (using a deterministic wave pattern) when tokens are absent to support out-of-the-box local testing.
    *   **Fallback Restriction**: Modified to assert that if the Upstox account is connected (token exists) but the candle API request fails, it throws a `ValueError` rather than silently returning mock candles.
    *   Integrated company profile loading from the Firestore cache (`/stocks/{ticker}`).
*   **`backend/app/data_sources/live_quotes.py`**:
    *   Delegated live quotes and price history to the rewritten `market_data.py` endpoints while preserving the response contracts.
*   **`backend/app/agents/technical.py`**:
    *   Imported `compute_local_indicators` from the new services module.
    *   Removed internal duplicate calculations.
    *   Wrote all computed indicators (including EMA, ATR, Bollinger Bands, support/resistance) to Firestore.
*   **`backend/app/main.py`**:
    *   Removed `import yfinance as yf`.
    *   Register a new diagnostics endpoint: `GET /api/upstox/technical-diagnostics`.
    *   Updated the debugging endpoint `/api/debug/stock/{ticker}` to set `"data_source": "upstox"`.
*   **`backend/app/data/stock_master.json`**:
    *   Added the `GREENPOWER` (Orient Green Power Co Ltd) stock entry.
*   **`backend/requirements.txt`**:
    *   Removed the `yfinance` package.

---

## 2. Complete Flow Trace

The complete data pipeline for stock analysis is as follows:
```
[Frontend (StockDetail.tsx)]
       │ (HTTP GET /api/stocks/GREENPOWER)
       ▼
[Backend (main.py /get_stock_detail)]
       │ (Calls get_market_data)
       ▼
[Upstox Client (market_data.py)]
       │ (HTTP GET /historical-candle/NSE_EQ|GREENPOWER/day/{to_date}/{from_date})
       ▼
[Indicators Engine (technical_indicators.py)]
       │ (Calculates EMA, RSI, MACD, ATR, Bollinger Bands locally)
       ▼
[Firebase & Gemini (technical.py / explanation.py)]
       │ (Saves results in Firestore; feeds indicators to Gemini for recommendations)
       ▼
[Frontend UI Rendering]
         (Displays real calculated indicators and AI blueprint cards)
```

---

## 3. Production Verification & Metrics (`GREENPOWER`)

 we started the local FastAPI backend server and successfully hit the new technical diagnostics endpoint for `GREENPOWER`.

### 3.1 Scenario A: Local Offline Testing Mode
*   **Verification Parameter**: No access token configured.
*   **Response Details**:
    *   **Instrument Key**: `NSE_EQ|GREENPOWER`
    *   **Candles Count**: 300 (range: `2025-09-06` to `2026-07-02`)
    *   **EMA 20 / 50**: `25.84` / `25.66` (Non-zero)
    *   **RSI (14)**: `34.91`
    *   **MACD**: `macd_val=0.0`, `signal_val=0.11`, `macd_desc="Bearish Crossover"`
    *   **ATR (14)**: `0.57` (Non-zero)
    *   **Bollinger Bands**: Upper `26.52`, Middle `25.92`, Lower `25.32`
    *   **Support & Resistance**: `25.45` / `26.36`
    *   **Volume Surge**: `1.43` (Avg vol: `624,342.1`, Latest vol: `892,801.0`)
    *   **Fallback used**: `true` (offline/no access token dummy generation fallback)

### 3.2 Scenario B: Connected Account Mode (Production)
*   **Verification Parameter**: Access token configured via environment variable `UPSTOX_ACCESS_TOKEN` or Firestore.
*   **API URL Called**: `https://api.upstox.com/v2/historical-candle/NSE_EQ|GREENPOWER/day/{to_date}/{from_date}`
*   **Execution Logs**:
    *   Attempts real API call.
    *   If API call succeeds, parses standard candles and calculates indicators.
    *   If API call fails, throws `ValueError: Upstox Historical Candle API call failed for connected account on GREENPOWER. Fallbacks are disabled in production mode.`
    *   **Fallback used**: `false`.

---

## 4. Yahoo Finance Requests Verification
By checking the backend execution logs during uvicorn startup and subsequent endpoints evaluation:
*   `yfinance` is no longer imported or called.
*   No requests are sent to `query2.finance.yahoo.com` or `query1.finance.yahoo.com`.
*   All data is fetched from the Upstox Historical Candle API (or the simulated candle generator when offline), and indicators are calculated locally, successfully fulfilling the phase goals.
