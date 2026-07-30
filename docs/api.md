# API Reference

This document references the complete list of REST API routes exposed by the FastAPI web server.

---

## 1. Core Endpoints Index

For detailed payload definitions, request schemas, and responses examples, refer to the primary **[docs/api_reference.md](./api_reference.md)**.

### 1.1 Auth & Connection Status
* `GET /api/upstox/auth-status`: Retrieve dynamic Upstox credentials age and current status.
* `GET /api/upstox/login`: Generates the redirect URL pointing to the broker's login page.
* `GET /api/upstox/callback`: OAuth callback route that exchanges the authorization code for an access token.

### 1.2 AI Portfolio Manager
* `GET /api/portfolio/holdings-analysis`: Runs Gemini holdings analysis over the current active portfolio.
* `GET /api/trading/risk-rules`: Retrieve active risk controls and exposure limits.
* `POST /api/trading/risk-rules`: Update exposure limits and target parameters inside Firestore.

### 1.3 Live Execution
* `GET /api/live/orders`: Returns the lists of recent completed and pending live trades.
* `GET /api/live/approve?order_id={id}`: Approves a pending transaction, routing it directly to Upstox.
* `GET /api/live/reject?order_id={id}`: Rejects a pending transaction, cancelling order execution.
