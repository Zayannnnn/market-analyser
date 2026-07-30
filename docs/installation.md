# Apex Stock Intelligence Engine: Installation Guide

This guide helps you set up the AORA platform locally and deploy it to Google Cloud Platform / Firebase.

---

## 1. System Requirements

* **Operating System**: Windows 10/11, macOS, or Linux
* **Python**: Version 3.12.x (Pins are in `.python-version` and `runtime.txt`)
* **Node.js**: Version 18.x or 20.x (with npm)
* **Firebase CLI**: Installed globally via `npm install -g firebase-tools`
* **Git**: Installed and configured

---

## 2. Repository Installation

### 2.1 Backend Setup
1. Open your terminal in the project's root folder.
2. Navigate to the backend directory:
   ```bash
   cd backend
   ```
3. Create a python virtual environment:
   ```bash
   python -m venv venv
   ```
4. Activate the virtual environment:
   * **Windows (PowerShell)**: `.\venv\Scripts\Activate.ps1`
   * **macOS/Linux**: `source venv/bin/activate`
5. Compile and install Python requirements:
   ```bash
   pip install -r requirements.txt
   ```
6. Copy the environment template and configure keys:
   ```bash
   cp .env.example .env
   ```
7. Place your Firebase `serviceAccountKey.json` credentials inside the `backend/` directory to enable Firestore connectivity.

### 2.2 Frontend Setup
1. Open another terminal in the project's root folder.
2. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
3. Install node dependencies:
   ```bash
   npm install
   ```
4. Configure local environment files (`.env.development`):
   ```
   VITE_API_BASE_URL=http://localhost:8000
   ```

---

## 3. Running Locally

### 3.1 Start Backend Web server
Inside your backend terminal (with active virtual environment):
```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
The FastAPI swagger docs will be accessible at: `http://localhost:8000/docs`

### 3.2 Start Frontend Dev Server
Inside your frontend terminal:
```bash
npm run dev
```
The web dashboard will open automatically on: `http://localhost:3000`

---

## 4. Firebase Cloud Deployment

Ensure you are logged into Firebase and have selected the appropriate active project:
```bash
firebase login
firebase use --add
```

### 4.1 Build and Deploy
1. Compile the React web application bundle:
   ```bash
   cd frontend
   npm run build
   ```
2. Deploy hosting and backend functions:
   ```bash
   cd ..
   firebase deploy --only hosting,functions
   ```
3. Add GCP project environment variables (`DASHBOARD_URL`, `GEMINI_API_KEY`, `UPSTOX_API_KEY`, `UPSTOX_API_SECRET`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`) inside the Google Cloud Run / Functions console configuration portal.
