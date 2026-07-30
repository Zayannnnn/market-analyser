# Apex Stock Intelligence Engine: Firestore Schema

This document details the Firestore database schemas, collections, indexes, and document structures utilized by AORA.

---

## 1. Collections Catalog

### 1.1 `stocks`
Stores technical indicators, current price metadata, and sector classifications.
* **Document ID**: `{ticker}` (e.g. `INFY`, `TCS`)
* **Fields**:
  * `company_name`: `string`
  * `sector`: `string`
  * `price`: `number` (float)
  * `change`: `number` (float, absolute change)
  * `change_pct`: `number` (float, percent change)
  * `rsi`: `number`
  * `macd`: `string` (`bullish` / `bearish` / `neutral`)
  * `trend`: `string` (`bullish` / `bearish` / `neutral`)
  * `support`: `number` (float)
  * `resistance`: `number` (float)
  * `atr`: `number` (float, Average True Range)
  * `updated_at`: `string` (ISO-8601 timestamp)

### 1.2 `news`
Stores matches of financial news articles processed by the Scraping engine.
* **Document ID**: Auto-generated UUID or Hash of title.
* **Fields**:
  * `ticker`: `string` (Matches document in `stocks`)
  * `title`: `string`
  * `link`: `string`
  * `source`: `string` (e.g., `Google News`)
  * `published_at`: `string` (ISO-8601 or raw RSS date)
  * `sentiment_score`: `number` (float, range: `-1.0` to `1.0`)
  * `sentiment_classification`: `string` (`positive` / `negative` / `neutral`)
  * `analysis_explanation`: `string` (AI reasoning)
  * `processed_at`: `string` (ISO-8601 timestamp)

### 1.3 `ai_analysis`
Caches Gemini-compiled growth and evaluation summaries for specific stock tickers.
* **Document ID**: `{ticker}`
* **Fields**:
  * `explanation`: `string` (Detailed analysis)
  * `confidence_score`: `number` (float, scale `0.0` to `10.0`)
  * `sentiment_summary`: `string`
  * `technical_summary`: `string`
  * `valuation_assessment`: `string`
  * `updated_at`: `string` (ISO-8601 timestamp)

### 1.4 `rankings`
Leaderboard rankings compiled by the Pipeline.
* **Document ID**: `current` (always points to the latest active rankings list)
* **Fields**:
  * `updated_at`: `string` (ISO-8601 timestamp)
  * `top_10`: `array` of maps containing:
    * `ticker`: `string`
    * `company_name`: `string`
    * `score`: `number`
    * `price`: `number`
    * `change_pct`: `number`

### 1.5 `user_alerts`
Alert settings configured by users.
* **Document ID**: Auto-generated
* **Fields**:
  * `user_id`: `string`
  * `ticker`: `string`
  * `target_score`: `number`
  * `alert_type`: `string` (`above_score` / `below_score` / `price_limit`)
  * `target_price`: `number` (float)
  * `is_triggered`: `boolean`
  * `created_at`: `string`

### 1.6 `config`
Authentication state and operational telemetry.
* **Document**: `upstox` (Stores access token)
  * `access_token`: `string`
  * `accessToken`: `string`
  * `updated_at`: `string`
* **Document**: `upstox_status` (Connection metrics)
  * `authentication_status`: `string` (`CONNECTED`, `EXPIRED`, `CONNECTING`, `ERROR`)
  * `last_successful_authentication`: `number` (float timestamp)
  * `last_expiry_alert`: `number` (float timestamp)
  * `last_processed_code`: `string`
* **Document**: `runtime_state` (Notification breakers, Task 2 details)
  * `upstox_connected`: `boolean`
  * `expiry_notification_sent`: `boolean`
  * `last_notification`: `number` (float timestamp)
  * `last_auth_check`: `number` (float timestamp)
* **Document**: `risk_rules` (Risk configuration parameters)
  * `max_portfolio_exposure_pct`: `number` (default: `80.0`)
  * `max_sector_exposure_pct`: `number` (default: `40.0`)
  * `max_single_stock_exposure_pct`: `number` (default: `20.0`)
  * `max_daily_loss_pct`: `number` (default: `5.0`)
  * `max_order_size_val`: `number` (default: `50000.0`)
  * `stop_loss_pct`: `number` (default: `10.0`)
  * `target_profit_pct`: `number` (default: `25.0`)

### 1.7 `live_trading`
Toggles and execution modes.
* **Document ID**: `config`
* **Fields**:
  * `mode`: `string` (`OFF`, `CONFIRM`, `AUTO`)
  * `live_trading_enabled`: `boolean`
  * `updated_at`: `string`

### 1.8 `paper_positions` & `paper_trades`
Simulated positions and trades history for Virtual/Paper trading.
* **Document ID**: Ticker (positions) or Transaction ID (trades)
* **Fields**:
  * `ticker`: `string`
  * `quantity`: `number`
  * `entry_price`: `number`
  * `stop_loss`: `number`
  * `take_profit`: `number`
  * `current_price`: `number`
  * `pnl`: `number`
  * `status`: `string` (`OPEN`, `CLOSED`, `FILLED`)
  * `created_at`: `string`
