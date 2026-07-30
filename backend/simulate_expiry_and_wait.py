import os
import sys
import time
from datetime import datetime

# Setup paths
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["FIREBASE_KEY_PATH"] = "backend/serviceAccountKey.json"

from app.db import db
from app.services.health_monitor import validate_upstox_token

def simulate_expiry():
    print("====================================================")
    print("SIMULATING EXPIRED TOKEN LIFE-CYCLE & SCHEDULER")
    print("====================================================")
    
    # 1. Back up current token and status
    doc_ref = db.collection("config").document("upstox")
    doc_snap = doc_ref.get()
    
    doc_status_ref = db.collection("config").document("upstox_status")
    status_snap = doc_status_ref.get()
    
    doc_live_ref = db.collection("live_trading").document("config")
    live_snap = doc_live_ref.get()
    
    backup_token = None
    if doc_snap.exists:
        backup_token = doc_snap.to_dict()
        print("[*] Successfully backed up active Upstox access token.")
    
    backup_status = None
    if status_snap.exists:
        backup_status = status_snap.to_dict()
        print("[*] Successfully backed up Upstox status indicators.")

    backup_live = None
    if live_snap.exists:
        backup_live = live_snap.to_dict()
        print("[*] Successfully backed up live trading configs.")
        
    try:
        # 2. Simulate expired session: set invalid access token in Firestore
        print("\n[*] Simulating expired token in Firestore config...")
        doc_ref.set({
            "access_token": "simulated_expired_token_for_validation_test",
            "accessToken": "simulated_expired_token_for_validation_test",
            "updated_at": datetime.utcnow().isoformat() + "Z"
        }, merge=True)
        
        # Reset last alert time to allow immediate reminder trigger
        print("[*] Resetting last_expiry_alert to 0.0 to clear quiet period throttling...")
        doc_status_ref.set({
            "last_expiry_alert": 0.0
        }, merge=True)
        
        # 3. Trigger validate_upstox_token()
        print("\n[*] Triggering validate_upstox_token() to simulate scheduled interval pipeline run...")
        val_res = validate_upstox_token()
        print(f"[*] Validation outcome: {val_res}")
        
        # 4. Check Firestore status updates
        print("\n[*] Reading updated Firestore telemetry...")
        updated_status = doc_status_ref.get().to_dict()
        print(f"  - authentication_status: {updated_status.get('authentication_status')}")
        print(f"  - last_expiry_alert: {updated_status.get('last_expiry_alert')}")
        print(f"  - last_alert_reason: {updated_status.get('last_alert_reason')}")
        
        updated_live = doc_live_ref.get().to_dict()
        print(f"  - live_trading_enabled: {updated_live.get('live_trading_enabled')} (Expected: False)")
        
        # Assert expectations
        assert val_res["valid"] is False, "Validation should identify token as invalid"
        assert updated_status["authentication_status"] == "EXPIRED", "Status should transition to EXPIRED"
        assert float(updated_status["last_expiry_alert"]) > 0.0, "Alert timestamp should be recorded"
        assert updated_live["live_trading_enabled"] is False, "Live trading breaker should be activated"
        
        print("\n[SUCCESS] E2E Simulation of token validation and alert dispatch completed successfully.")
        
    except Exception as e:
        print(f"\n[FAILURE] E2E Simulation failed: {e}")
        
    finally:
        # 5. Restore backups
        print("\n[*] Restoring original configuration snapshots...")
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
    simulate_expiry()
