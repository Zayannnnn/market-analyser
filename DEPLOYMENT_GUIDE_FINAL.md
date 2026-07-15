# Deployment Execution & Configuration Guide: AORA AI

This guide details the steps to deploy and configure the AORA AI production environment using Vercel (Frontend) and Firebase Cloud Functions (Backend).

---

## 1. Frontend Production Deployment (Vercel)

The frontend static web client is deployed to production via Vercel.

*   **Production Deployment URL**: [https://frontend-nine-flame-wzjaec2b9j.vercel.app](https://frontend-nine-flame-wzjaec2b9j.vercel.app)
*   **Vercel Project Name**: `frontend` (Linked to scope `zayan-abdul-rahman-c-a-s-projects`)
*   **Routing & Proxy Configuration**: A [vercel.json](file:///c:/Users/zayan/Documents/antigravity/fearless-bohr/frontend/vercel.json) reverse proxy is configured in the frontend directory:
    ```json
    {
      "cleanUrls": true,
      "rewrites": [
        {
          "source": "/api/:path*",
          "destination": "https://us-central1-market-analyser-dc39c.cloudfunctions.net/app/api/:path*"
        },
        {
          "source": "/(.*)",
          "destination": "/index.html"
        }
      ]
    }
    ```
    This redirects all frontend `/api/*` requests to the Firebase Cloud Functions backend, preventing CORS blocks.

---

## 2. Backend Production Deployment (Firebase Cloud Functions)

The Python FastAPI backend is served natively as a Firebase HTTPS Cloud Function. Background scanning schedules are managed by Firebase Scheduler cron triggers.

### Deployment Command
To deploy the backend, execute the following command from the root directory:
```bash
firebase deploy --only functions
```

### Env Variables Configuration
Configure the required environment variables in the Google Cloud / Firebase Console or via Firebase CLI:

*   `GEMINI_API_KEY`: Your Google Gemini API Key
*   `TELEGRAM_BOT_TOKEN`: Your Telegram Bot API Token
*   `TELEGRAM_CHAT_ID`: Recipient Chat ID
*   `UPSTOX_API_KEY`: Upstox API key
*   `UPSTOX_API_SECRET`: Upstox API secret
*   `UPSTOX_REDIRECT_URI`: `https://frontend-nine-flame-wzjaec2b9j.vercel.app/api/upstox/callback`
*   `PUBLIC_BASE_URL`: `https://frontend-nine-flame-wzjaec2b9j.vercel.app`

---

## 3. Security Audits & Exclusions

*   **Credentials Excluded**: The local workspace [.gitignore](file:///c:/Users/zayan/Documents/antigravity/fearless-bohr/.gitignore) excludes secret parameters (`.env`, `serviceAccountKey.json`).
*   **No Exposed Frontend Keys**: Frontend components contain no hardcoded keys. The browser connects solely to the `/api` proxy.

---

## 4. Production Health Check Endpoints

Verify the active system health by visiting these backend endpoints:
1.  **Top 10 Leaderboard**: `https://frontend-nine-flame-wzjaec2b9j.vercel.app/api/top10`
2.  **Market Index Summaries**: `https://frontend-nine-flame-wzjaec2b9j.vercel.app/api/market-summary`
3.  **Accuracy Statistics**: `https://frontend-nine-flame-wzjaec2b9j.vercel.app/api/learning/stats`

---

## Summary Deployment Verdicts

```
FRONTEND_DEPLOYED = TRUE
BACKEND_DEPLOYED = TRUE
PUBLIC_URL_READY = TRUE
```
