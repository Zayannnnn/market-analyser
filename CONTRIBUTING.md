# Contributing to AORA Engine

Thank you for your interest in contributing to the AORA Engine! This guide outlines the processes and standards for contributing code, tests, and documentation.

---

## 1. Project Overview
AORA (Apex Stock Intelligence Engine) is a production-grade AI-assisted stock intelligence and automated trading platform for Indian markets. It features a FastAPI backend, a React frontend, and a multi-agent framework integrated with Gemini AI, Firebase, and the Upstox API.

---

## 2. Local Development Setup

### 2.1 Backend Setup
1. Navigate to the backend folder:
   ```bash
   cd backend
   ```
2. Create and activate a python virtual environment:
   ```bash
   python -m venv venv
   # On Windows: .\venv\Scripts\Activate.ps1
   # On macOS/Linux: source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy the environment variables template and configure it:
   ```bash
   cp .env.example .env
   ```
5. Place your Google Cloud service account keys inside the backend folder as `serviceAccountKey.json`.
6. Start the development server:
   ```bash
   python -m uvicorn app.main:app --port 8000 --reload
   ```

### 2.2 Frontend Setup
1. Navigate to the frontend folder:
   ```bash
   cd frontend
   ```
2. Install node packages:
   ```bash
   npm install
   ```
3. Start the dev server:
   ```bash
   npm run dev
   ```

---

## 3. Style & Standards Guide

### 3.1 Git Branch Naming Conventions
* **Features**: `feature/your-feature-name`
* **Bug Fixes**: `fix/bug-description`
* **Documentation**: `docs/topic-name`
* **Performance Optimizations**: `perf/what-was-optimized`

### 3.2 Commit Message Conventions
We follow standard conventional commits formats:
* `feat: add Zerodha broker integration`
* `fix: prevent Telegram alert spam on token expiration`
* `docs: update API endpoints guides`
* `test: append unit tests for risk engine`

### 3.3 Coding Style
* **Python**: Follow PEP 8 style guidelines.
* **TypeScript / React**: Use modern functional components with hooks. Prefer explicit type declarations.

---

## 4. Pull Request Workflow

1. Fork the repository and check out a clean branch from `master`.
2. Implement your changes, ensuring code is clean and readable.
3. Write matching unit tests under the `backend/` folder following the `test_*.py` format.
4. Verify all tests pass locally:
   ```bash
   python -m unittest backend/test_auth_notifications.py
   python -m unittest backend/test_portfolio_manager.py
   python -m unittest backend/test_trading.py
   ```
5. Commit your work and push to your fork.
6. Submit a Pull Request targeting the `master` branch.
7. Ensure all CI pipeline checks pass successfully.
