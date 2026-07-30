# Security Policy Reference

This document maps the security architectural guardrails, policies, and disclosure guidelines enforced in AORA Engine.

---

## 1. Core Policies Index

Refer to the primary **[SECURITY.md](../SECURITY.md)** for:
* Reporting vulnerabilities and reporting addresses.
* Security response timelines.
* Support matrices.

---

## 2. Technical Vulnerabilities Review

For the detailed audit of technical vulnerabilities, secrets protection, token expiry monitoring loops, and database isolation checks, refer to the **[docs/security/security_report.md](./security/security_report.md)** (formerly `security_report.md` in the root directory).

* Key aspects covered:
  * Upstox OAuth session verification.
  * Pausing live execution instantly upon token invalidation.
  * Preventing Telegram alert spam via `config/runtime_state` checks.
  * Firestore database read/write isolation rules.
