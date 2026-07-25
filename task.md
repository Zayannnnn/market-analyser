# AORA - AI Stock Intelligence Migration Tasks

## Phase 3.1: Analysis and Architecture [COMPLETE]
- [x] Inspect the complete repository
- [x] Understand current architecture and microservices layout
- [x] Identify and catalog all yfinance and Yahoo Finance API dependencies
- [x] Locate all frontend components displaying Yahoo-derived values
- [x] Document all placeholder and fallback values triggered during Yahoo Finance throttling
- [x] Create a migration design replacing Yahoo Finance with Upstox & Local computations
- [x] Create dynamic news summarization architecture using RSS & Gemini
- [x] Design AI recommendation expansion in Python and UI layouts
- [x] Update `task.md` with audit details
- [x] Produce detailed implementation plan and report in `walkthrough.md`

## Phase 3.2: Implementation [COMPLETE]
- [x] Set up local Python environment and configure standard libraries and dependencies
- [x] Replace Yahoo Finance historical candle retrieval with Upstox Historical Candle API in `market_data.py`
- [x] Preserve response structure in `live_quotes.py` by delegating to Upstox endpoints
- [x] Create reusable indicators module `backend/app/services/technical_indicators.py` in local Python
- [x] Implement local calculations: EMA 20, EMA 50, RSI 14, MACD, ATR 14, Bollinger Bands (20,2), Support & Resistance, Volume Analysis, and Breakout Detection
- [x] Update technical analysis agent in `agents/technical.py` to consume the new indicators module
- [x] Remove hardcoded placeholder fallbacks (EMA=0, ATR=0, MACD Neutral, RSI=50) when valid candles exist
- [x] Register test stock `GREENPOWER` in `stock_master.json`
- [x] Implement dynamic caching lookup service `backend/app/services/instrument_lookup.py` to resolve symbols to their official Upstox `instrument_key` (via the S3/Cloudfront Beginning-of-Day Instruments Master GZIP data) instead of hardcoding `NSE_EQ|{ticker}` format.
- [x] Create technical diagnostics endpoint `/api/upstox/technical-diagnostics` in `main.py`
- [x] Verify calculations for `GREENPOWER`, `BEL`, `RELIANCE`, and `TCS` (confirming proper instrument key mapping like `NSE_EQ|INE999K01014` and validation URLs).
- [x] Confirm no Yahoo Finance requests are executed
- [x] Update task list in `task.md` and document changes in `walkthrough.md`
- [x] Commit and prepare for deployment

## Phase 3.3: Production Verification [COMPLETE]
- [x] Restrict fallback generator in production (fail loudly if authenticated account fails to pull candles)
- [x] Search and verify complete elimination of yfinance/Yahoo/synth references in codebase
- [x] Remove dead code and dummy indicators fallbacks
- [x] Build interactive production verification utility `verify_production.py` to execute non-mocked requests using live Upstox account tokens
- [x] Update walkthrough.md and task.md

## Phase 3.4: Final Live Production Verification [COMPLETE]
- [x] Retrieve serviceAccountKey.json and copy to active backend folder
- [x] Map config database path to config/upstox_auth
- [x] Query and verify live Upstox candles and local indicator calculations for GREENPOWER, BEL, and RELIANCE
- [x] Confirm exact calculated values propagate to Firestore
- [x] Purge simulated candle generators and fallbacks from market_data.py completely
- [x] Verify zero leftover Yahoo/placeholder references in backend and frontend
- [x] Create automated deployment helper script deploy.ps1 for Cloud Run and Vercel

## Phase 4.1: Upstox Trading Service & AI Trade Review [COMPLETE]
- [x] Create app/services/upstox_trading.py with place/cancel/modify/get order functions
- [x] Create app/services/order_logger.py to save attempts to Firestore
- [x] Create app/services/ai_trade_review.py for Gemini Flash review synthesis
- [x] Update app/models.py with pydantic schemas for requests, responses, and AI reviews
- [x] Implement FastApi routes in app/main.py
- [x] Build React frontend component frontend/src/components/TradingPanel.tsx
- [x] Register TradingPanel in frontend routes and UI navigation
- [x] Verify everything works E2E and run unit tests

