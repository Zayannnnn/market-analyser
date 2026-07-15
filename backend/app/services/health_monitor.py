import logging
import time
import httpx
from datetime import datetime
from typing import Dict, Any, List
from app.db import db
from app.config import settings
from app.data_sources.market_data import upstox_client
from app.services.live_execution import get_live_execution_mode, set_live_execution_mode, send_telegram_order_alert

logger = logging.getLogger(__name__)

# Failsafe and Health state
LAST_HEALTH_METRICS = {}

def measure_latency(service_name: str, start_time: float):
    """Logs structured latency metrics (Task 5)."""
    duration_ms = int((time.time() - start_time) * 1000)
    logger.info(f"[OBSERVABILITY] Service: {service_name} | Latency: {duration_ms}ms")
    return duration_ms

def trigger_auth_reminder(reason: str):
    """Sends one Telegram authentication alert and updates Firestore status."""
    try:
        status_ref = db.collection("config").document("upstox_status")
        status_doc = status_ref.get()
        now_ts = time.time()
        
        last_alert = 0.0
        if status_doc.exists:
            last_alert = float(status_doc.to_dict().get("last_expiry_alert", 0.0))
            
        # Send alert if no alert was sent in the last 12 hours (prevents duplicates)
        if now_ts - last_alert > 43200:
            bot_token = settings.telegram_bot_token
            chat_id = settings.telegram_chat_id
            login_url = settings.public_login_url
            
            text = f"""
🔐 <b>AORA Authentication Required</b>

Your Upstox session has expired.

Live Trading: <b>PAUSED</b>

Paper Trading: <b>RUNNING</b>

AI Analysis: <b>RUNNING</b>

Scheduler: <b>ACTIVE</b>

Reconnect using:
<a href="{login_url}">{login_url}</a>
"""
            if bot_token and chat_id:
                url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                httpx.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"}, timeout=5.0)
                
            status_ref.set({
                "authentication_status": "EXPIRED",
                "last_expiry_alert": now_ts,
                "last_alert_reason": reason
            }, merge=True)
            logger.info("Sent Telegram authentication required reminder.")
    except Exception as e:
        logger.error(f"Error triggering auth reminder: {e}")

def validate_upstox_token() -> Dict[str, Any]:
    """Validates the currently loaded Upstox OAuth token (Task 6)."""
    start_time = time.time()
    token = upstox_client.get_access_token()
    now_ts = time.time()
    
    status_ref = db.collection("config").document("upstox_status")
    
    if not token:
        latency = measure_latency("Upstox Token Validation", start_time)
        reason = "No token available in Firestore or Environment."
        
        # Pause live trading
        db.collection("live_trading").document("config").set({
            "live_trading_enabled": False,
            "updated_at": datetime.utcnow().isoformat() + "Z"
        }, merge=True)
        
        trigger_auth_reminder(reason)
        
        status_ref.set({
            "authentication_status": "EXPIRED",
            "last_health_check": now_ts,
            "last_health_check_status": "EXPIRED"
        }, merge=True)
        
        return {"valid": False, "reason": reason, "latency_ms": latency}
        
    try:
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }
        res = httpx.get("https://api.upstox.com/v2/user/profile", headers=headers, timeout=5.0)
        latency = measure_latency("Upstox Token Validation", start_time)
        
        if res.status_code == 200:
            status_ref.set({
                "authentication_status": "CONNECTED",
                "last_health_check": now_ts,
                "last_health_check_status": "CONNECTED"
            }, merge=True)
            return {"valid": True, "reason": "Token verified successfully.", "latency_ms": latency}
            
        elif res.status_code == 401:
            reason = f"Expired or unauthorized (Upstox Code 401): {res.text}"
            
            # Pause live trading
            db.collection("live_trading").document("config").set({
                "live_trading_enabled": False,
                "updated_at": datetime.utcnow().isoformat() + "Z"
            }, merge=True)
            
            trigger_auth_reminder(reason)
            
            status_ref.set({
                "authentication_status": "EXPIRED",
                "last_health_check": now_ts,
                "last_health_check_status": "EXPIRED"
            }, merge=True)
            return {"valid": False, "reason": reason, "latency_ms": latency}
            
        else:
            reason = f"Upstox status {res.status_code}: {res.text}"
            
            # Pause live trading
            db.collection("live_trading").document("config").set({
                "live_trading_enabled": False,
                "updated_at": datetime.utcnow().isoformat() + "Z"
            }, merge=True)
            
            trigger_auth_reminder(reason)
            
            status_ref.set({
                "authentication_status": "ERROR",
                "last_health_check": now_ts,
                "last_health_check_status": "ERROR",
                "last_error_reason": reason
            }, merge=True)
            return {"valid": False, "reason": reason, "latency_ms": latency}
            
    except Exception as e:
        latency = measure_latency("Upstox Token Validation", start_time)
        reason = f"HTTP Exception: {e}"
        
        # Pause live trading
        db.collection("live_trading").document("config").set({
            "live_trading_enabled": False,
            "updated_at": datetime.utcnow().isoformat() + "Z"
        }, merge=True)
        
        trigger_auth_reminder(reason)
        
        status_ref.set({
            "authentication_status": "ERROR",
            "last_health_check": now_ts,
            "last_health_check_status": "ERROR",
            "last_error_reason": reason
        }, merge=True)
        return {"valid": False, "reason": reason, "latency_ms": latency}

def get_firestore_health() -> Dict[str, Any]:
    """Measures Firestore read/write latency (Task 3 & 5)."""
    start_time = time.time()
    try:
        # Perform a mock write and read
        test_ref = db.collection("live_trading").document("health_ping")
        test_ref.set({"ping": "pong", "timestamp": time.time()})
        doc = test_ref.get()
        latency = measure_latency("Firestore Health Check", start_time)
        if doc.exists and doc.to_dict().get("ping") == "pong":
            return {"status": "CONNECTED", "latency_ms": latency}
        return {"status": "DEGRADED", "reason": "Ping mismatch", "latency_ms": latency}
    except Exception as e:
        latency = measure_latency("Firestore Health Check", start_time)
        return {"status": "DISCONNECTED", "reason": str(e), "latency_ms": latency}

def get_gemini_health() -> Dict[str, Any]:
    """Checks Gemini API response latency (Task 3 & 5)."""
    start_time = time.time()
    try:
        from google import genai
        # Simple health check client test
        api_key = settings.gemini_api_key
        if not api_key:
            return {"status": "DISCONNECTED", "reason": "GEMINI_API_KEY environment variable missing.", "latency_ms": 0}
            
        # Call a tiny verification prompt
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents='health_check_ok'
        )
        latency = measure_latency("Gemini API Health Check", start_time)
        if response.text:
            return {"status": "CONNECTED", "latency_ms": latency}
        return {"status": "DEGRADED", "reason": "Empty Gemini response", "latency_ms": latency}
    except Exception as e:
        latency = measure_latency("Gemini API Health Check", start_time)
        return {"status": "DISCONNECTED", "reason": str(e), "latency_ms": latency}

def get_internet_health() -> Dict[str, Any]:
    """Verifies internet connection latency (Task 3 & 5)."""
    start_time = time.time()
    try:
        res = httpx.get("https://www.google.com", timeout=3.0)
        latency = measure_latency("Internet Health Check", start_time)
        if res.status_code == 200:
            return {"status": "CONNECTED", "latency_ms": latency}
        return {"status": "DEGRADED", "reason": f"Status {res.status_code}", "latency_ms": latency}
    except Exception as e:
        latency = measure_latency("Internet Health Check", start_time)
        return {"status": "DISCONNECTED", "reason": str(e), "latency_ms": latency}

def get_scheduler_health() -> Dict[str, Any]:
    """Retrieves current scheduler status metadata (Task 3)."""
    try:
        doc = db.collection("paper_scheduler").document("status").get()
        if doc.exists:
            d = doc.to_dict()
            return {"status": d.get("status", "ACTIVE"), "last_scan": d.get("last_scan_time")}
        return {"status": "UNKNOWN", "last_scan": None}
    except Exception as e:
        return {"status": "DISCONNECTED", "reason": str(e)}

def trigger_system_failsafe(reason: str):
    """
    Failsafe Mode (Task 4).
    If critical components (Upstox auth, Firestore, Internet) fail:
    - Disable AUTO/CONFIRM live trading modes.
    - Cancel pending approval orders.
    - Record incident.
    - Alert via Telegram.
    """
    logger.critical(f"[FAILSAFE TRIGGERED] Tripping safety breaker: {reason}")
    
    # 1. Force set Mode to OFF in Firestore configurations
    set_live_execution_mode("OFF")
    
    # 2. Cancel any pending orders waiting for manual confirmation
    cancelled_count = 0
    try:
        pending_orders = db.collection("live_orders") \
                          .where("status", "==", "PENDING_APPROVAL") \
                          .get()
        for doc in pending_orders:
            o_id = doc.id
            db.collection("live_orders").document(o_id).update({
                "status": "REJECTED_SAFETY",
                "broker_response": f"Failsafe mode triggered: System safety breaker tripped: {reason}"
            })
            cancelled_count += 1
    except Exception as e:
        logger.error(f"Error cancelling pending orders during failsafe: {e}")

    # 3. Record incident logs in Firestore
    incident_id = f"failsafe_{int(time.time() * 1000)}"
    incident = {
        "incident_id": incident_id,
        "reason": reason,
        "cancelled_orders_count": cancelled_count,
        "timestamp": time.time(),
        "created_at": datetime.utcnow().isoformat() + "Z",
        "recovered": False,
        "resolved_at": None
    }
    try:
        db.collection("live_trading").document("incidents").set(incident)
    except Exception as e:
        logger.error(f"Error saving incident log to Firestore: {e}")

    # 4. Dispatch alert to Telegram chat
    try:
        bot_token = settings.telegram_bot_token
        chat_id = settings.telegram_chat_id
        if bot_token and chat_id:
            text = f"""
<b>⚠️ CRITICAL SYSTEM FAILSAFE RUN</b>
Safety Breaker Status: <b>🚨 TRIPPED</b>
Reason: <i>{reason}</i>
Live Trading Mode: <b>OFF (Trading Suspended)</b>
Cancelled Pending Orders: <b>{cancelled_count}</b>
Timestamp: <b>{datetime.now().isoformat()}</b>
"""
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            httpx.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"}, timeout=5.0)
    except Exception as e:
        logger.error(f"Failed to dispatch failsafe alert via Telegram: {e}")

def run_system_health_checks() -> Dict[str, Any]:
    """Runs E2E health validation routines across critical modules (Task 3)."""
    global LAST_HEALTH_METRICS
    
    # 1. Evaluate individual systems
    upstox = validate_upstox_token()
    firestore = get_firestore_health()
    gemini = get_gemini_health()
    internet = get_internet_health()
    scheduler = get_scheduler_health()
    
    # Determine overall Health Score (0 - 100)
    # Weights: Upstox validation (40%), Firestore check (20%), Gemini API (15%), Internet link (15%), Scheduler heartbeat (10%)
    score = 100
    details = []
    
    if not upstox["valid"]:
        score -= 40
        details.append(f"Upstox Session Offline: {upstox['reason']}")
    if firestore["status"] != "CONNECTED":
        score -= 20
        details.append(f"Firestore database failure: {firestore.get('reason')}")
    if gemini["status"] != "CONNECTED":
        score -= 15
        details.append(f"Gemini API failure: {gemini.get('reason')}")
    if internet["status"] != "CONNECTED":
        score -= 15
        details.append(f"Internet connection failure: {internet.get('reason')}")
    if scheduler["status"] != "ACTIVE":
        score -= 10
        details.append(f"Scheduler heartbeat offline: {scheduler.get('status')}")
        
    overall_score = max(0, score)
    
    # Failsafe check (Task 4): If Upstox token is invalid or database or internet is offline, trip Safety Breaker
    active_mode = get_live_execution_mode()
    if overall_score < 70 and active_mode != "OFF":
        failsafe_reason = ", ".join(details) if details else "Aggregated health score fell below safe boundaries (70%)."
        trigger_system_failsafe(failsafe_reason)
        active_mode = "OFF"
        
    # Get last order metadata
    last_order_ref = db.collection("live_orders").order_by("created_timestamp", direction="DESCENDING").limit(1).get()
    last_order = None
    if last_order_ref:
        last_order = last_order_ref[0].to_dict()
        
    # Resolve last incident metadata
    incident_ref = db.collection("live_trading").document("incidents").get()
    current_incident = None
    if incident_ref.exists:
        current_incident = incident_ref.to_dict()
        
    metrics = {
        "health_score": overall_score,
        "upstox_status": "CONNECTED" if upstox["valid"] else "DISCONNECTED",
        "upstox_reason": upstox["reason"],
        "upstox_latency_ms": upstox["latency_ms"],
        "firestore_status": firestore["status"],
        "firestore_latency_ms": firestore["latency_ms"],
        "gemini_status": gemini["status"],
        "gemini_latency_ms": gemini["latency_ms"],
        "internet_status": internet["status"],
        "internet_latency_ms": internet["latency_ms"],
        "scheduler_status": scheduler["status"],
        "mode": active_mode,
        "last_order": last_order,
        "current_incident": current_incident,
        "timestamp": time.time(),
        "created_at": datetime.utcnow().isoformat() + "Z"
    }
    
    # Cache metrics in Firestore
    try:
        db.collection("live_trading").document("health_metrics").set(metrics)
    except Exception as e:
        logger.error(f"Failed to cache health metrics to Firestore: {e}")
        
    LAST_HEALTH_METRICS = metrics
    return metrics
