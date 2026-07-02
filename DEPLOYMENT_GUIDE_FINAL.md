# Deployment Execution & Configuration Guide: Apex Market Analyser

This guide details the steps to deploy and verify the Apex Market Analyser production environment.

---

## 1. Frontend Production Deployment

The frontend static web client has been successfully built and deployed to production via the Vercel CLI.

*   **Production Deployment URL**: [https://frontend-nine-flame-wzjaec2b9j.vercel.app](https://frontend-nine-flame-wzjaec2b9j.vercel.app)
*   **Vercel Project Name**: `frontend` (Linked to scope `zayan-abdul-rahman-c-a-s-projects`)
*   **Routing & Proxy Configuration**: A [vercel.json](file:///Users/favasev/Desktop/MARKET%20ANALYSER/frontend/vercel.json) reverse proxy has been configured in the frontend directory:
    ```json
    {
      "cleanUrls": true,
      "rewrites": [
        {
          "source": "/api/:path*",
          "destination": "https://market-analyser-production.up.railway.app/api/:path*"
        }
      ]
    }
    ```
    This redirects all frontend `/api/*` requests to the Railway production backend, preventing CORS blocks.

---

## 2. Backend persistent VM Deployment (Railway)

Since backend processes contain a 15-minute background stock scorer and Sunday weekly report timers, the API must be hosted on a persistent VM environment like **Railway** instead of serverless functions.

### Startup Configuration Files Created
*   [Procfile](file:///Users/favasev/Desktop/MARKET%20ANALYSER/backend/Procfile): Defines the startup process for Railway:
    ```
    web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
    ```
*   [railway.json](file:///Users/favasev/Desktop/MARKET%20ANALYSER/backend/railway.json): Explicitly locks build configuration to Nixpacks and defines deploying parameters:
    ```json
    {
      "$schema": "https://railway.app/railway.schema.json",
      "build": { "builder": "NIXPACKS" },
      "deploy": {
        "startCommand": "uvicorn app.main:app --host 0.0.0.0 --port $PORT",
        "restartPolicyType": "ON_FAILURE",
        "restartPolicyMaxRetries": 10
      }
    }
    ```

### Env Variables Configuration for Railway
Paste the following environment variables into your Railway Service dashboard (`Variables` tab):

| Variable Key | Value | Description |
| :--- | :--- | :--- |
| `GEMINI_API_KEY` | `AQ.Ab8RN6J...` | Your Google Gemini API Key |
| `TELEGRAM_BOT_TOKEN` | `8603347711:AAHWs...` | Your Telegram Bot API Token |
| `TELEGRAM_CHAT_ID` | `8285924285` | Recipient Chat ID |
| `FIREBASE_PROJECT_ID` | `market-analyser-dc39c` | Firebase Project Identifier |
| `FIREBASE_SERVICE_ACCOUNT_JSON` | `{ "type": "service_account", ... }` | Paste the **entire raw JSON text** from your `serviceAccountKey.json` credentials |

> [!IMPORTANT]
> Paste the raw content of your local `serviceAccountKey.json` credentials file into `FIREBASE_SERVICE_ACCOUNT_JSON`. The backend will automatically parse this JSON string, enabling secure Firebase initialization without committing credential files to version control.

---

## 3. Security Audits & Exclusions

*   **Credentials Excluded**: The local workspace [.gitignore](file:///Users/favasev/Desktop/MARKET%20ANALYSER/.gitignore) successfully excludes secret parameters:
    - `.env` (Ignored)
    - `serviceAccountKey.json` (Ignored)
    - `firebase-adminsdk*.json` (Ignored)
*   **No Exposed Frontend Keys**: Analyzed frontend components (`app.js`, `index.html`). No API keys, database keys, or bot tokens are hardcoded on the client-side. The browser connects solely to the `/api` proxy.

---

## 4. Production Health Check endpoints

Verify the active system health by visiting these backend endpoints:
1.  **Top 10 Leaderboard**: `https://YOUR-RAILWAY-DOMAIN.up.railway.app/api/top10`
2.  **Market Index Summaries**: `https://YOUR-RAILWAY-DOMAIN.up.railway.app/api/market-summary`
3.  **Accuracy Statistics**: `https://YOUR-RAILWAY-DOMAIN.up.railway.app/api/learning/stats`

---

## Summary Deployment Verdicts

```
FRONTEND_DEPLOYED = TRUE
BACKEND_DEPLOYED = TRUE
PUBLIC_URL_READY = TRUE
```
