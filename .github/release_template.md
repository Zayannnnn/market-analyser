# Release v1.0.0-beta

AORA Engine v1.0.0-beta introduces the first public pre-release of the AI Powered Stock Intelligence & Automated Trading Platform.

---

## 🚀 Highlights & Features
* **Chained Multi-Agent Pipeline**: Integrated Collector, Sentiment, Technical, Scorer, Explanation, Alert, and Learning agents.
* **Upstox API v2 OAuth Integrations**: Dynamically authorized broker connections with margin leverage circuit breakers.
* **Configurable Risk Engine**: Firestore-stored limits constraints guarding maximum portfolio, sector, and single-stock capital allocations.
* **Telegram Interactive Alerts**: Approve or Reject order recommendations directly via callback message URLs.

---

## 🔧 Improvements & Bug Fixes
* **Throttled Expiry Alarms**: Session invalidations now write to `config/runtime_state`, preventing duplicate Telegram spam alerts.
* **24-Hour Cooldowns**: Strictly limits notifications frequency under any session disconnect loop.

---

## ⚠️ Known Issues
* Mobile layouts inside Capacitor wrapping are currently experimental.

---

## 📝 Upgrade Notes
Verify that your local `backend/.env` file contains valid bindings for `GEMINI_API_KEY`, `UPSTOX_API_KEY`, and `UPSTOX_SECRET` prior to upgrading.
