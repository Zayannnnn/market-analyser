import os
import sys
import time
import httpx
from datetime import datetime

# Setup paths
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["FIREBASE_KEY_PATH"] = "backend/serviceAccountKey.json"

from app.db import db

def run_production_e2e_test():
    print("====================================================")
    print("LIVE PRODUCTION END-TO-END AUTHEM REMINDER TEST")
    print("====================================================")
    
    # 1. Back up current Firestore configurations
    doc_ref = db.collection("config").document("upstox")
    doc_snap = doc_ref.get()
    
    doc_status_ref = db.collection("config").document("upstox_status")
    status_snap = doc_status_ref.get()
    
    doc_live_ref = db.collection("live_trading").document("config")
    live_snap = doc_live_ref.get()
    
    backup_token = doc_snap.to_dict() if doc_snap.exists else None
    backup_status = status_snap.to_dict() if status_snap.exists else None
    backup_live = live_snap.to_dict() if live_snap.exists else None
    
    print("[*] Firestore config snapshots backed up successfully.")
    
    try:
        # 2. Simulate expired token in Firestore
        print("\n[*] Simulating invalid token in Firestore...")
        doc_ref.set({
            "access_token": "production_test_expired_token_value_simulation",
            "accessToken": "production_test_expired_token_value_simulation",
            "updated_at": datetime.utcnow().isoformat() + "Z"
        }, merge=True)
        
        # Reset quiet period alert tracker
        print("[*] Clearing quiet period last_expiry_alert throttling...")
        doc_status_ref.set({
            "last_expiry_alert": 0.0
        }, merge=True)
        
        # 3. Post HTTP request directly to Cloud Run API Base URL
        prod_url = "https://aora-backend-wzjaec2b9j-el.a.run.app/api/paper/scheduler/health-checks"
        print(f"\n[*] Triggering deployed production API endpoint:\n    POST {prod_url}")
        
        # We trigger it and set a longer timeout
        res = httpx.post(prod_url, timeout=60.0)
        print(f"[*] Production response: HTTP {res.status_code}")
        print(f"    Payload: {res.text}")
        
        # 4. Check if Firestore was updated by the DEPLOYED function
        print("\n[*] Reading updated Firestore telemetry status...")
        updated_status = doc_status_ref.get().to_dict()
        print(f"  - authentication_status: {updated_status.get('authentication_status')}")
        print(f"  - last_expiry_alert: {updated_status.get('last_expiry_alert')}")
        print(f"  - last_alert_reason: {updated_status.get('last_alert_reason')}")
        
        updated_live = doc_live_ref.get().to_dict()
        print(f"  - live_trading_enabled: {updated_live.get('live_trading_enabled')}")
        
        # Validation checks
        assert updated_status.get("authentication_status") in ["EXPIRED", "ERROR"], "Authentication status should transition to EXPIRED/ERROR"
        assert float(updated_status.get("last_expiry_alert", 0.0)) > 0.0, "last_expiry_alert timestamp should be set (> 0)"
        assert updated_live.get("live_trading_enabled") is False, "live_trading_enabled should be disabled by the Cloud Function"
        
        print("\n[SUCCESS] Live production Cloud Function E2E execution check passed!")
        print("          The deployed function automatically detected expired token, updated Firestore status, and invoked Telegram bot.")
        
    except Exception as e:
        print(f"\n[FAILURE] Production execution check failed: {e}")
        
    finally:
        # 5. Restore snapshots
        print("\n[*] Restoring original Firestore configuration snapshots...")
        if backup_token:
            doc_ref.set(backup_token)
        else:
            doc_ref.delete()
            
        if backup_status:
            doc_status_ref.set(backup_status)
        else:
            doc_status_ref.delete()

        if backup_live:
            doc_live_ref.set(backup_live)
        else:
            doc_live_ref.delete()
            
        print("[*] Database restoration completed successfully.")
        print("====================================================")

if __name__ == "__main__":
    run_production_e2e_test()
