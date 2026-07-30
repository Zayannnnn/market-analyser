# Changelog
All notable changes to the AORA Engine project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0-beta] - 2026-07-31

### Added
* **AI News Engine**: Real-time financial RSS scrape integrations with deduplication and ticker symbol matching.
* **Gemini Analysis**: Chained news sentiment evaluations and Growth Catalyst Explanations using Gemini 2.5 Flash.
* **Portfolio Intelligence**: Comprehensive web dials displaying total capital, used margin, buying power, and holdings weight allocations.
* **Risk Engine**: Deterministic rules validators enforcing exposure limits (80% portfolio cap, 40% sector cap, 20% single stock cap) and margin check guardrails.
* **Upstox Integration**: Dynamic token authentication (OAuth v2 flow) E2E checker and REST execution wraps.
* **Telegram Alerts**: Interactive alerts with click-to-approve links and connections status checks.
* **React Dashboard**: Premium dark-mode UI containing TradingView charts and risk rule editor sliders.
* **FastAPI Backend**: Wrapped ASGI endpoints matching firebase Cloud Run/Functions deployment parameters.
