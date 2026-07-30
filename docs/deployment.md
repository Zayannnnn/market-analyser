# Deployment Guide Reference

This document maps the production deployment configurations for the AORA Engine stack.

---

## 1. Core Guides Index

For complete step-by-step instructions on deploying the React web frontend, configuring Google Cloud Run, setting up Cloud Function triggers, and running verifications, refer to:
* **[docs/deployment/deployment_guide.md](./deployment/deployment_guide.md)**: Main deployment guide.
* **[docs/deployment/DEPLOYMENT_GUIDE_FINAL.md](./deployment/DEPLOYMENT_GUIDE_FINAL.md)**: Consolidated setup walkthroughs.
* **[docs/reports/BACKEND_DEPLOYMENT_REPORT.md](./reports/BACKEND_DEPLOYMENT_REPORT.md)**: Cloud Run deployment audit report.

---

## 2. Infrastructure Summary

* **Frontend Hosting**: Vercel (primary) or Firebase Hosting (alternative fallback via `firebase.json`).
* **Backend Runtime**: Google Cloud Run (FastAPI ASGI via Docker container, configured to automatically fetch environment secrets and Firestore bindings).
* **Scheduling Triggers**: Google Cloud Scheduler (invokes FastAPI webhook routes during market intervals).
