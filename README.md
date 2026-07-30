# AORA: Apex Stock Intelligence Engine

<div align="center">

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-007ACC?style=for-the-badge&logo=typescript&logoColor=white)](https://www.typescriptlang.org)
[![Gemini](https://img.shields.io/badge/Gemini-8E75C2?style=for-the-badge&logo=googlegemini&logoColor=white)](https://deepmind.google/technologies/gemini)
[![Firebase](https://img.shields.io/badge/Firebase-FFCA28?style=for-the-badge&logo=firebase&logoColor=black)](https://firebase.google.com)
[![License](https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

<h3>A production-grade, multi-agent AI Stock Valuation & Automated Trading platform. Built for the Indian Stock Market.</h3>

[System Architecture](./docs/architecture.md) • [API Guide](./docs/api_reference.md) • [Firestore Schema](./docs/firestore_schema.md) • [AI Agents Guide](./docs/ai_agents.md) • [Telegram Setup](./docs/telegram_integration.md) • [Developer Guide](./docs/developer_guide.md) • [Installation Guide](./docs/installation.md)

</div>

---

## 1. System Overview

**AORA (Apex Stock Intelligence Engine)** is an automated portfolio manager and trade execution platform. It scrapes real-time news, polls price indicators, runs weighted score rankings, resolves growth catalysts using Gemini, and routes executions to the Upstox API.

```
       [RSS News Feeds]        [Historical Prices]
              │                         │
              ▼                         ▼
      ┌───────────────┐         ┌───────────────┐
      │Sentiment Agent│         │Technical Agent│
      └───────┬───────┘         └───────┬───────┘
              │                         │
              └───────────┬─────────────┘
                          ▼
                  ┌───────────────┐
                  │ Scorer Agent  │ (Weighted Rank Aggregation)
                  └───────┬───────┘
                          ▼
                  ┌───────────────┐
                  │Leaderboard    │ (Rankings Current Collection)
                  └───────┬───────┘
                          ▼
                  ┌───────────────┐
                  │Risk Engine    │ (Exposure Check & Cash Allocation)
                  └───────┬───────┘
                          ▼
              ┌───────────────────────┐
              │    Execution Layer    │
              ├───────────┬───────────┤
              │           │           │
              ▼           ▼           ▼
           [ OFF ]    [CONFIRM]    [ AUTO ]
              │           │           │
           (Ignore)  (Telegram Approval) (Direct Trade API)
```

---

## 2. Platform Architecture

AORA utilizes a decoupled, serverless system topology where the Python FastAPI engine is wrapped using `a2wsgi` middleware to run inside Firebase Cloud Functions.

```mermaid
graph TD
    subgraph Client Application
        ReactWeb["React + Vite Frontend (Web/Localhost)"]
    end

    subgraph Firebase cloud services
        Firestore[("Firestore Database\n(Stocks, Orders, Runtime State)")]
        CloudFunctions["Firebase Cloud Functions\n(FastAPI ASGI via a2wsgi)"]
    end

    subgraph External APIs
        Upstox["Upstox API\n(OAuth, Profiles, Portfolio, Trading)"]
        Gemini["Gemini AI\n(Analyses, Explanations, Reviews)"]
        Telegram["Telegram Bot API\n(Alerts, Interactive Buttons)"]
        GoogleNews["Google News RSS\n(Feed Scrapes)"]
    end

    ReactWeb <-->|REST APIs| CloudFunctions
    CloudFunctions <-->|Read / Write| Firestore
    CloudFunctions -->|Analyze| Gemini
    CloudFunctions -->|Fetch & Trade| Upstox
    CloudFunctions -->|Notify| Telegram
    CloudFunctions -->|Scrape| GoogleNews
    Telegram -->|Callback Hooks| CloudFunctions
```

---

## 3. Directory Layout

The project structure is organized as follows:

```
├── .firebaserc
├── firebase.json
├── deploy.ps1
├── backend/
│   ├── main.py (Cloud Functions entrypoint)
│   ├── requirements.txt (Dependencies list)
│   ├── runtime.txt
│   ├── .python-version (Python 3.12 pin)
│   ├── app/
│   │   ├── main.py (FastAPI Routes & Middlewares)
│   │   ├── config.py (Pydantic Settings)
│   │   ├── db.py (Firestore client initialization)
│   │   ├── scheduler.py (Automation Cron loops)
│   │   ├── agents/
│   │   │   ├── news_collector.py (Google News RSS scrapes)
│   │   │   ├── sentiment.py (Gemini news sentiment analysis)
│   │   │   ├── technical.py (Technical indicators poller)
│   │   │   └── ranking.py (Valuation rankings aggregator)
│   │   └── services/
│   │       ├── risk_engine.py (Exposures & Limits validators)
│   │       ├── live_execution.py (Upstox trade routers)
│   │       ├── health_monitor.py (Token checks & safety breakers)
│   │       └── upstox_trading.py (Upstox client SDK wrappers)
│   └── test_auth_notifications.py (Unit tests for rate limiters)
└── frontend/
    ├── package.json
    ├── vite.config.js
    └── src/
        ├── App.tsx
        └── components/
            ├── PortfolioIntelligence.tsx (Cash dials & AI recommendations)
            └── LiveExecution.tsx (Trade logs & Risk configurations)
```

---

## 4. API Endpoints Catalog

Here is a summary of primary routes exposed by the FastAPI server. See the [API Guide](./docs/api_reference.md) for JSON schemas.

| Method | Endpoint | Description | Cache Status |
|---|---|---|---|
| `GET` | `/api/top10` | Ranked stock leaderboard | Cached (15 mins) |
| `GET` | `/api/stocks/{ticker}` | Indicators & news detail | Database Read |
| `GET` | `/api/stocks/{ticker}/research` | DCF & Catalysts Memo | Stale-Check & Compile |
| `GET` | `/api/upstox/auth-status` | Dynamic OAuth credentials age | Database Read |
| `GET` | `/api/upstox/login` | Redirect to Upstox Dialog | Dynamic |
| `GET` | `/api/upstox/callback` | Exch Code for Access Token | Write & Redirect |
| `POST`| `/api/trading/buy` | Execute buy suggestions | Risk Validated |
| `GET` | `/api/live/approve` | Approve order from Telegram | Trigger Execution |

---

## 5. Quickstart Installation

Detailed configurations can be found in the [Installation Guide](./docs/installation.md).

### 5.1 Backend Local Setup
```bash
cd backend
python -m venv venv
# Windows: .\venv\Scripts\Activate.ps1 | Unix: source venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --port 8000 --reload
```

### 5.2 Frontend Local Setup
```bash
cd frontend
npm install
npm run dev
```

---

## 6. Execution Safety & Cooldown Rules

* **Single Message Limit**: During token expiration events, AORA writes state flags to Firestore (`config/runtime_state`). It dispatches exactly **ONE** Telegram message to avoid notification floods.
* **24-Hour Cooldown**: A strict 24-hour rate limit check prevents multiple notification alerts even if credentials expire and reconnect loops cycle repeatedly.
* **Leverage Circuit Breaker**: Live trading is paused immediately upon token expiration, while paper trading and analytics loops continue. When the user reconnects, flags are reset and live trading resumes.

---

## 7. Future Roadmap

- [ ] **Multi-Broker Routing**: Support Zerodha Kite and Angel One wrappers.
- [ ] **Advanced Backtester UI**: Interactive chart parameters for custom strategy definitions.
- [ ] **On-Device LLM Fallback**: Run lightweight localized models (e.g. Gemma 2B) for basic offline scans.
- [ ] **Capacitor Mobile Build**: Cross-platform configurations mapping to Android devices.

---

## 8. License

Distributed under the MIT License. See [LICENSE](LICENSE) for more information.
