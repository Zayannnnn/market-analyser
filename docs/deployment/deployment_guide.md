# Production Deployment Guide: AI Stock Intelligence Engine

This document provides step-by-step instructions to configure, run, and deploy the AI-powered Market Analyser system (FastAPI backend + Next.js/HTML dashboard frontend).

---

## Prerequisites

Ensure you have the following installed on your system:
- **Python 3.9+** (For the backend FastAPI server)
- **Node.js 18+** & **npm** (For the frontend dev server)
- A **Google Cloud / Firebase Account** (For Firestore database)
- A **Google Gemini API Key** (For sentiment and analysis agents)
- A **Telegram Bot Token** (For Agent 6 notifications)

---

## Step 1: Firebase Firestore Setup

1. Open the [Firebase Console](https://console.firebase.google.com/) and click **Add Project**.
2. Name your project (e.g. `market-analyser`) and click continue.
3. In the left navigation, click **Build** -> **Firestore Database** and click **Create Database**.
4. Set the location (e.g., `asia-south1` for India) and start in **Production mode**.
5. Once created, click on the **Project Settings** (gear icon next to Project Overview).
6. Go to the **Service Accounts** tab.
7. Click **Generate New Private Key** and download the resulting JSON file. Keep this secure; it contains admin credentials for your database.
8. Save this file on your local machine (e.g. `firebase-credentials.json`) and copy its path.

---

## Step 2: Telegram Bot Integration

1. In the Telegram app, search for the official **@BotFather** bot.
2. Send `/newbot` and follow the instructions to name your bot and choose a username.
3. Copy the generated **HTTP API Token** (this is your `TELEGRAM_BOT_TOKEN`).
4. To find your Chat ID, message **@userinfobot** or add your bot to a channel/group, make it an administrator, and send a test message.
5. Retrieve your numeric Chat/Channel ID (this is your `TELEGRAM_CHAT_ID`).

---

## Step 3: Local Environment Configuration

1. In the `backend/` directory, copy `.env.example` to a new file named `.env`:
   ```bash
   cp backend/.env.example backend/.env
   ```
2. Open `backend/.env` and fill in the parameters:
   *   `GEMINI_API_KEY`: Your Google AI Studio key.
   *   `FIREBASE_SERVICE_ACCOUNT_PATH`: The absolute file path to the JSON certificate downloaded in Step 1. (Omit if deploying on Google Cloud Run/AppEngine where ADC is automatic).
   *   `TELEGRAM_BOT_TOKEN`: The API key copied from @BotFather.
   *   `TELEGRAM_CHAT_ID`: The channel/chat ID to send alerts to.

---

## Step 4: Run the Backend Locally

1. Create a Python virtual environment and activate it:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
2. Navigate to the `backend/` directory and install the requirements:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```
3. Start the FastAPI development server:
   ```bash
   uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```
4. Access the API documentation (Swagger UI) at: `http://localhost:8000/docs`

*Note: On startup, the server automatically starts the background scheduler and checks Firestore. If the database is empty, it initializes the default NSE tickers list (BEL, RELIANCE, TCS, etc.) and runs the pipeline once to seed the collections.*

---

## Step 5: Run the Frontend Locally

1. Open a new terminal window and navigate to the `frontend/` directory:
   ```bash
   cd frontend
   ```
2. Install the dev server dependencies:
   ```bash
   npm install
   ```
3. Launch the Vite local server:
   ```bash
   npm run dev
   ```
4. Open the dashboard at `http://localhost:3000` to interact with the real data stream!

---

## Step 6: Deploying to Vercel (Production)

### 1. Deploying the FastAPI Backend

1. Install the Vercel CLI globally:
   ```bash
   npm install -g vercel
   ```
2. Navigate to the `backend/` folder and log in to Vercel:
   ```bash
   cd backend
   vercel login
   ```
3. Run the deployment command:
   ```bash
   vercel --prod
   ```
4. During setup, configure the following **Environment Variables** in the Vercel Dashboard Settings for the project:
   *   `GEMINI_API_KEY`
   *   `TELEGRAM_BOT_TOKEN`
   *   `TELEGRAM_CHAT_ID`
   *   `FIREBASE_SERVICE_ACCOUNT_PATH` (or upload the JSON contents directly as a string configuration parameter if needed).
5. Capture your deployed production URL (e.g. `https://market-analyser-api.vercel.app`).

### 2. Deploying the Frontend

1. Open `frontend/app.js`.
2. Locate the `API_BASE` configuration at the top of the file:
   ```javascript
   const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' 
     ? 'http://localhost:8000/api' 
     : 'https://your-vercel-backend-api-url.vercel.app/api';
   ```
   Replace `https://your-vercel-backend-api-url.vercel.app` with the actual backend production URL generated in the previous step.
3. Deploy the `frontend/` folder as a static site on Vercel:
   ```bash
   cd ../frontend
   vercel --prod
   ```

---

## Step 7: Scheduler Execution in Serverless (Vercel) Environments

Because Vercel serverless functions shut down when not serving active requests, APscheduler will not run in the background indefinitely in serverless deployments. 

To maintain the 15-minute data refresh cycle in production, you should use **Vercel Cron Jobs** or an external cron scheduler (such as **Cron-Job.org** or **Upstash**):
*   Configure a Cron job to trigger a `POST` request to `https://your-vercel-backend-api-url.vercel.app/api/analyze-stocks` every 15 minutes.
*   This endpoint runs the pipeline in the background and updates Firestore.
*   The frontend queries the cached Firestore collection, guaranteeing a load time of under 3 seconds.
