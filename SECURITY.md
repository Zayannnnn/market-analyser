# Security Policy for AORA Engine

We take security vulnerabilities seriously. This document outlines supported versions, security architectures, and instructions on reporting flaws.

---

## 1. Supported Versions

The following versions of AORA are currently supported with security updates:

| Version | Supported | Notes |
|---|---|---|
| v1.0.x | Yes | Current stable release series. |
| < v1.0.0 | No | Legacy versions. Please upgrade. |

---

## 2. Reporting a Vulnerability

Do NOT report security vulnerabilities via public GitHub issues. Instead, please report vulnerabilities by email to the repository owner at `zayan@zayan.dev` or via the secure disclosure paths on GitHub.

### Security Response Timeline
* **Acknowledgment**: Within 48 hours of receipt.
* **Assessment**: Within 5 business days, including verification and impact classification.
* **Mitigation**: Security patches will be merged and released within 14 business days.

---

## 3. Security Architecture & Guardrails

### 3.1 Secrets Handling
* Never commit `.env` files or API secrets.
* Service account credentials (`serviceAccountKey.json`) must be excluded via `.gitignore`.
* Production API secrets (`GEMINI_API_KEY`, `UPSTOX_SECRET`, `TELEGRAM_BOT_TOKEN`) must be loaded from serverless runtime environment settings.

### 3.2 Upstox OAuth Security
* Access tokens are stored inside Firestore `config/upstox_auth` and loaded dynamically.
* The system validates token freshness via the `/v2/user/profile` endpoint. If verification returns a 401 Unauthorized error, the system disables live trading instantly, logs out the session, and triggers a single Telegram alert.

### 3.3 Firestore Security Rules
Ensure your Firestore Rules block unauthorized reads and writes:
```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /config/{document} {
      allow read, write: if request.auth != null && request.auth.uid == "OWNER_UID";
    }
    match /stocks/{document} {
      allow read: if true;
      allow write: if request.auth != null;
    }
  }
}
```
