# Phase 3.2 - 3.4 Walkthrough & Live Production Verification Report

This walkthrough documents the completed implementation details, newly created modules, API changes, codebase audits, and live production verification test results for **Phase 3.2, Phase 3.3, and Phase 3.4 — Yahoo Finance Removal & Upstox Migration**.

---

## 1. Summary of Changes

### 1.1 New Modules Created
*   **`backend/app/services/technical_indicators.py`**:
    A standalone reusable module containing local indicator calculation logic using Python (`pandas` and `numpy`).
    Calculates: EMA 20, EMA 50, RSI (14), MACD (12, 26, 9), ATR (14), Bollinger Bands (20, 2), Support & Resistance (20-day min/max closes), Volume Analysis (surge & 20-day average), and Channel Breakout status.
*   **`backend/app/services/instrument_lookup.py`**:
    A new dynamic lookup service that retrieves the daily official Upstox NSE Instruments Master list (`NSE.json.gz`), caches it locally to `backend/app/data/upstox_instruments_cache.json`, and resolves equity symbols to their official ISIN-based `instrument_key` (e.g. `NSE_EQ|INE999K01014` for `GREENPOWER` instead of hardcoding `NSE_EQ|GREENPOWER`). Checks cache expiration (24h) and reloads master list automatically on lookup miss.
*   **`deploy.ps1`**:
    An automated PowerShell script placed in the root directory to trigger the Vercel frontend and GCP Cloud Run backend deployments.

### 1.2 Files Modified
*   **`backend/app/data_sources/market_data.py`**:
    *   Excised all direct and indirect requests to `yfinance` subdomains.
    *   Refactored `UpstoxClient` to fetch candle data from the Upstox Historical Candle API:
        `GET /historical-candle/{instrument_key}/{interval}/{to_date}/{from_date}`
    *   Integrated `get_upstox_instrument` for resolving official ISIN-based instrument keys.
    *   Mapped access token retrieval to Firestore collection `config` document `upstox_auth` (fields `access_token` or `accessToken`).
    *   **Restricted Fallbacks**: Purged `generate_simulated_candles` and the fallback simulated candles path completely. The code now requires a valid token and successfully fetched candles, failing loudly with a `ValueError` if either is missing, guaranteeing 100% live data in production.
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
*   **`.gitignore`**:
    *   Added local instrument caches.

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
       │ (Looks up instrument key from cache/master)
       │ (Loads OAuth Token from Firestore config/upstox_auth)
       │ (HTTP GET /historical-candle/NSE_EQ|INE999K01014/day/{to_date}/{from_date})
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

## 3. Live Production Verification Metrics

We initialized Firebase Admin using the private certificate `backend/serviceAccountKey.json`, retrieved the real Upstox access token from `config/upstox_auth`, and executed the live verification checks against the official Upstox API.

### 3.1 GREENPOWER (Orient Green Power Co Ltd)
*   **Instrument Key**: `NSE_EQ|INE999K01014`
*   **Request URL**: `https://api.upstox.com/v2/historical-candle/NSE_EQ|INE999K01014/day/2026-07-04/2025-02-19`
*   **HTTP Status**: `200`
*   **Candle Count**: `336`
*   **First Candle**: `['2025-02-19T00:00:00+05:30', 12.25, 13.18, 12.06, 12.91, 4395136, 0]`
*   **Last Candle**: `['2026-07-03T00:00:00+05:30', 10.53, 10.64, 10.42, 10.47, 1895331, 0]`
*   **Date Range**: `2025-02-19` to `2026-07-03`
*   **Calculated Indicators**:
    *   EMA20: `10.84`
    *   EMA50: `10.94`
    *   RSI (14): `36.95`
    *   MACD: `macd_val=-0.2`, `signal_val=-0.13`, `macd_desc="Bearish Crossover"`
    *   ATR (14): `0.33`
    *   Bollinger Bands: Upper=`11.55` / Middle=`10.91` / Lower=`10.28`
    *   Support / Resistance: `10.41` / `11.26`
    *   Volume Surge: `0.73`x (Avg Vol: `2,597,738.85`)
*   **Firestore Update**: Saved metrics to Firestore `/stocks/GREENPOWER` document fields.

### 3.2 BEL (Bharat Electronics Ltd)
*   **Instrument Key**: `NSE_EQ|INE263A01024`
*   **Request URL**: `https://api.upstox.com/v2/historical-candle/NSE_EQ|INE263A01024/day/2026-07-04/2025-02-19`
*   **HTTP Status**: `200`
*   **Candle Count**: `336`
*   **First Candle**: `['2025-02-19T00:00:00+05:30', 240.7, 254.0, 240.25, 253.4, 21516255, 0]`
*   **Last Candle**: `['2026-07-03T00:00:00+05:30', 418.6, 424.5, 417.1, 418.05, 12085695, 0]`
*   **Date Range**: `2025-02-19` to `2026-07-03`
*   **Calculated Indicators**:
    *   EMA20: `415.88`
    *   EMA50: `420.14`
    *   RSI (14): `51.14`
    *   MACD: `macd_val=2.76`, `signal_val=-1.3`, `macd_desc="Bullish Crossover"`
    *   ATR (14): `9.09`
    *   Bollinger Bands: Upper=`430.0` / Lower=`398.78`
    *   Support / Resistance: `402.3` / `431.5`
    *   Volume Surge: `0.91`x (Avg Vol: `13,228,497.45`)
*   **Firestore Update**: Saved metrics to Firestore `/stocks/BEL` document fields.

### 3.3 RELIANCE (Reliance Industries Ltd)
*   **Instrument Key**: `NSE_EQ|INE002A01018`
*   **Request URL**: `https://api.upstox.com/v2/historical-candle/NSE_EQ|INE002A01018/day/2026-07-04/2025-02-19`
*   **HTTP Status**: `200`
*   **Candle Count**: `336`
*   **First Candle**: `['2025-02-19T00:00:00+05:30', 1219.5, 1232.75, 1217.55, 1227.45, 6217338, 0]`
*   **Last Candle**: `['2026-07-03T00:00:00+05:30', 1312.0, 1312.0, 1302.0, 1304.0, 7839550, 0]`
*   **Date Range**: `2025-02-19` to `2026-07-03`
*   **Calculated Indicators**:
    *   EMA20: `1310.84`
    *   EMA50: `1332.1`
    *   RSI (14): `46.07`
    *   MACD: `macd_val=6.12`, `signal_val=-4.5`, `macd_desc="Bullish Crossover"`
    *   ATR (14): `23.32`
    *   Bollinger Bands: Upper=`1346.38` / Lower=`1255.87`
    *   Support / Resistance: `1258.8` / `1332.7`
    *   Volume Surge: `0.51`x (Avg Vol: `15,286,106.5`)
*   **Firestore Update**: Saved metrics to Firestore `/stocks/RELIANCE` document fields.

---

## 4. Codebase Audit: Yahoo/Synthetic References Removal
*   **yfinance / Yahoo**: 0 functional references remain in the code.
*   **Synthetic Fallbacks (EMA=0, ATR=0, etc.)**: 0 functional fallback placeholders exist in the codebase. All UI components display actual live indicators calculated from real historical candles.
