# Apex Stock Intelligence Engine: Telegram Bot Integration

AORA integrates with the Telegram Bot API to dispatch instant market alerts, portfolio status summaries, and interactive callback buttons for trade approval.

---

## 1. Bot Setup & Configuration

To integrate the notification system, the following configuration parameters are loaded from backend environments (`.env`):
* `TELEGRAM_BOT_TOKEN`: The unique API access token provided by `@BotFather`.
* `TELEGRAM_CHAT_ID`: The unique identifier of the target user chat, group, or channel.

*Note: Chat IDs can be resolved automatically using the utility script `backend/resolve_chat_id.py` which polls `getUpdates` to match user commands.*

---

## 2. Notification Message Layouts

All Telegram notifications are sent as HTML-formatted messages using `httpx`.

### 2.1 Expired Session Alert
Sent immediately when `validate_upstox_token()` encounters a `401 Unauthorized` or empty token:

```
🔐 <b>AORA Authentication Required</b>

Your Upstox session has expired.

Live Trading: <b>PAUSED</b>
Paper Trading: <b>RUNNING</b>
AI Analysis: <b>RUNNING</b>
Scheduler: <b>ACTIVE</b>

Reconnect using:
<a href="{login_url}">{login_url}</a>
```

### 2.2 Broker Connection Success Alert
Sent upon successful Upstox login and E2E token validation:

```
🟢 <b>AORA Connected</b>

Broker: Upstox
Authentication: Successful

Live Trading: <b>READY</b>
Paper Trading: <b>RUNNING</b>
AI Analysis: <b>RUNNING</b>
Scheduler: <b>ACTIVE</b>

Authenticated At: {auth_time} IST
Expected Expiry: {expiry_time} IST
```

### 2.3 Interactive Trade Review Alert (CONFIRM Mode)
Sent when the opportunity scanner triggers a buy setup under `CONFIRM` mode:

```
⚠️ <b>AI Trade Review: Action Required</b>

Ticker: <b>{ticker}</b>
Direction: <b>{action}</b>
Quantity: <b>{qty} shares</b>
Estimated Price: <b>₹{price}</b>
Total Value: <b>₹{total_val}</b>

<b>AI Catalyst Analysis:</b>
{reasoning}

<b>Risk Engine checks:</b>
- Max single stock exposure: PASSED
- Sector exposure cap: PASSED
- Cash balance checklist: PASSED

Review links:
👉 <a href="{api_base}/api/live/approve?order_id={order_id}">APPROVE ORDER</a>
❌ <a href="{api_base}/api/live/reject?order_id={order_id}">REJECT ORDER</a>
```

---

## 3. Callback Interaction Flow

When the user clicks the `APPROVE ORDER` link inside their Telegram client:
1. The Telegram client opens the link, sending a GET request to the AORA backend endpoint `/api/live/approve?order_id={order_id}`.
2. The FastAPI backend validates the order signature in Firestore.
3. It validates available buying power and places the actual order on Upstox.
4. Returns an HTML response showing connection confirmation, and fires a second Telegram alert showing order receipt details.
5. If the user clicks `REJECT ORDER`, the backend updates the Firestore order status to `REJECTED_MANUAL` and skips routing.
