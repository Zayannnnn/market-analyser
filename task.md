# AORA - AI Stock Intelligence Migration Tasks

## Phase 3.1: Analysis and Architecture [IN PROGRESS]
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

## Phase 3.2: Implementation [PLANNED]
- [ ] Implement Upstox Historical Candle API ingestion for stock history and indices
- [ ] Implement local indicators engine in Python (EMA 20, EMA 50, RSI, MACD, ATR, Bollinger Bands, Support/Resistance, Volume Analysis)
- [ ] Create Firestore fundamentals caching mechanism (Company Profile, sector, PE, Dividend Yield, High/Low etc.)
- [ ] Connect news scraper to Gemini summarization pipeline producing Sentiment & Impact metrics
- [ ] Upgrade Gemini agent explanation prompt to return structural trade blueprints (entry, target, stop loss, confidence %, risk score)
- [ ] Refactor frontend `StockDetail.tsx` to display real indicator numbers and the AI Blueprint cards
- [ ] Refactor frontend `Dashboard.tsx` to pull all market overview indices from Upstox
- [ ] Perform local integration testing and verify logs and error boundaries
- [ ] Prepare final production audit and deploy to Google Cloud Run and Vercel
