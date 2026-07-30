# Getting Started with AORA Engine

Follow this guide to set up the AORA platform locally on your machine.

---

## 1. System Requirements
Ensure your local environment meets these parameters:
* **Python**: `3.12.x` (pins are loaded in `.python-version` and `runtime.txt`)
* **Node.js**: `v18.x` or `v20.x` (with npm)
* **Git**: Installed and configured

---

## 2. OS Quickstart Installation

### 2.1 Windows (PowerShell)
```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env
# Place your serviceAccountKey.json file inside /backend
python -m uvicorn app.main:app --port 8000 --reload
```

### 2.2 Linux & macOS
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Place your serviceAccountKey.json file inside /backend
python3 -m uvicorn app.main:app --port 8000 --reload
```

---

## 3. Frontend Setup
In a separate terminal window:
```bash
cd frontend
npm install
npm run dev
```
The application will open automatically at: `http://localhost:3000`
