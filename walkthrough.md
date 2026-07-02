# Phase 3.1 Walkthrough & Implementation Plan: Yahoo Finance Removal

This document outlines the detailed findings and implementation plan for Phase 3.1 of the AORA AI Stock Intelligence platform migration. This phase focuses entirely on auditing the codebase, identifying Yahoo Finance dependencies, and drafting the target architecture. No modifications are being deployed at this stage.

---

## 1. Audit Report

### 1.1 Yahoo Finance Dependencies
We searched the codebase and identified reference files, functions, and elements importing `yfinance` or making raw HTTP requests to Yahoo Finance subdomains:

*   **Files:**
    1.  `backend/requirements.txt`: Reference to `yfinance==0.2.40`
    2.  `backend/app/data_sources/live_quotes.py`: Imports `yfinance as yf` and references `query1.finance.yahoo.com` and `query2.finance.yahoo.com` in `_fetch_chart` and `_fetch_profile`.
    3.  `backend/app/data_sources/market_data.py`: Imports `yfinance as yf` and performs raw HTTP chart lookups to Yahoo.
    4.  `backend/app/main.py`: Imports `yfinance as yf` and sets debug source to `"yfinance"`.
    5.  `backend/scratch_audit.py`: Developer test file importing `yfinance`.
*   **Functions:**
    *   `fetch_live_quote()` (live_quotes.py)
    *   `fetch_price_history()` (live_quotes.py)
    *   `get_market_data()` (market_data.py)
    *   `_fetch_chart()`, `_fetch_profile()` (live_quotes.py)
*   **Frontend Components:**
    *   `Dashboard.tsx` (Market Overview indexes, Top 10 prices, change, and scores)
    *   `StockDetail.tsx` (Interactive historical chart, gauges, Support/Resistance bars, corporate fundamentals card)
    *   `IndexDetail.tsx` (Index overview details and historical charts)
*   **Placeholder & Fallback Values:**
    Under Yahoo API throttling, the system falls back to empty values:
    *   RSI = `50.0` (Neutral)
    *   MACD = `"Neutral"`
    *   SMA 50 vs 200 = `0.0` / `0.0`
    *   Volume Surge = `1.0`
    *   Breakout Status = `False`
    *   Support & Resistance = `None`
    *   AI Rating Confidence = `"Medium"`
    *   Fundamentals = `"Unavailable"` or `None`

---

## 2. Migration Architecture

The new architecture will completely remove all dependencies on `yfinance` and direct Yahoo HTTP calls. It will replace them with:

1.  **Upstox Historical Candle API** for historical close/volume streams, moving averages, and index tracking.
2.  **Local Python calculations** for all technical indicators.
3.  **Firestore fundamentals caching** to store corporate profile info (Sector, PE, Dividend Yield, High/Low) once and serve them instantly without external queries.
4.  **RSS news sources** integrated with Gemini Flash to generate digests, sentiment scores, and impact rankings.
5.  **AI Recommendation Blueprint** that details target prices, stop losses, and confidence stats in a unified card.

### 2.1 Access Token Strategy
We will update `UpstoxClient` in `backend/app/data_sources/market_data.py` to retrieve the access token dynamically from either the `UPSTOX_ACCESS_TOKEN` environment variable or the Firestore config document (`config/upstox`), allowing seamless execution in serverless contexts.

### 2.2 Local Indicators Calculations
*   **EMA 20 & 50:** Calculated via pandas `ewm(span=N, adjust=False).mean()`.
*   **RSI (14):** Wilder's standard EWM formula.
*   **MACD (12, 26, 9):** Local EMA subtraction and signal lines.
*   **ATR (14):** Average True Range calculated from the High, Low, and Close prices of historical daily candles.
*   **Bollinger Bands (20, 2):** 20-period SMA middle band, $\pm$ 2 standard deviations for Upper/Lower bands.
*   **Support & Resistance:** 52-week min/max close calculations from the historical candles.
*   **Volume Analysis:** 20-day simple average comparison.

---

## 3. UI Redesign Plan

We will enrich `StockDetail.tsx` with a premium visual presentation:

1.  **AI Investment Blueprint Card**:
    *   **Recommendation Badge**: BUY (green), HOLD (yellow), SELL (red) in bold styles.
    *   **Metrics Grid**: Confidence % bar, Risk Score dial, and Expected Holding Period.
    *   **Blueprint Columns**: Entry Price, Target Price, Stop Loss.
    *   **Reasoning Block**: Gemini-generated brief explaining the trade structure.
2.  **News Feed Summaries**:
    *   Display Gemini-generated summaries, sentiment pills (Bullish/Bearish/Neutral), and impact levels (High/Medium/Low) for each matching article.
3.  **Expanded Gauge Panels**:
    *   Incorporate Bollinger Bands and ATR values alongside RSI and MACD.

---

## 4. Verification Checklists
- [ ] Run `run_pipeline.py` and inspect logs to verify 0 requests are routed to Yahoo Finance.
- [ ] Assert local calculations (EMA, RSI, MACD, ATR, Bollinger Bands) against static datasets.
- [ ] Open the frontend page and verify no fallback placeholders or "Throttle" messages are visible.
