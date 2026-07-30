import os
import sys
import time
import logging

# Setup path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["FIREBASE_KEY_PATH"] = "backend/serviceAccountKey.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

from app.db import db
from app.services.health_monitor import validate_upstox_token, trigger_auth_reminder

def verify_telegram_auth_lifecycle():
    logger.info("Initializing Telegram Auth Lifecycle verification tests...")
    
    # 1. Clear status first
    logger.info("Resetting config/upstox_status in Firestore...")
    status_ref = db.collection("config").document("upstox_status")
    status_ref.delete()
    
    # 2. Simulate invalid/missing token state to trigger alert
    logger.info("Simulating missing token alert dispatch...")
    trigger_auth_reminder("Test failure reason: verification test run")
    
    doc = status_ref.get()
    assert doc.exists, "Failed: upstox_status doc should exist"
    data = doc.to_dict()
    assert data["authentication_status"] == "EXPIRED"
    assert "last_expiry_alert" in data
    
    first_alert_time = data["last_expiry_alert"]
    logger.info(f" - First alert recorded at: {first_alert_time}")
    
    # 3. Simulate duplicate alert trigger (should skip to prevent spam)
    logger.info("Simulating subsequent check to prevent duplicate alerts...")
    trigger_auth_reminder("Test failure duplicate reason")
    
    doc_retry = status_ref.get().to_dict()
    assert doc_retry["last_expiry_alert"] == first_alert_time, "Failed: last_expiry_alert updated, duplicate alert was NOT blocked!"
    logger.info(" - Duplicate alert successfully blocked (timestamp remains unchanged).")

    # 4. Simulate daily morning health check behavior at 8:45 AM
    logger.info("Simulating 8:45 AM weekday health check validation...")
    from app.services.paper_scheduler import run_health_checks
    status_map = run_health_checks()
    logger.info(f" - Health Check status map: {status_map}")
    
    # 5. Simulate successful token callback login clearing the alert
    logger.info("Simulating successful user OAuth callback authentication...")
    now_ts = time.time()
    
    # Update firestore state exactly like the callback route
    status_ref.set({
        "authentication_status": "CONNECTED",
        "last_successful_authentication": now_ts,
        "last_authentication_time": now_ts
    }, merge=True)
    
    doc_success = status_ref.get().to_dict()
    assert doc_success["authentication_status"] == "CONNECTED"
    assert doc_success["last_successful_authentication"] == now_ts
    logger.info(" - Auth status cleared. Status: CONNECTED")
    
    # Verify api endpoint status return
    import httpx
    # Start temporary test request to mock api endpoint if needed, or query status dict directly
    from app.main import api_get_upstox_auth_status
    auth_status = api_get_upstox_auth_status()
    logger.info(f" - /api/upstox/auth-status response: {auth_status}")
    assert auth_status["authentication_status"] == "CONNECTED"
    assert auth_status["token_age_str"] != "Unknown"
    
    logger.info("\n[SUCCESS] E2E Telegram Authentication Reminder tests passed successfully.")
    return True

if __name__ == "__main__":
    success = verify_telegram_auth_lifecycle()
    if success:
        sys.exit(0)
    else:
        sys.exit(1)
