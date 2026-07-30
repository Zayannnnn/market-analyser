import os
import sys
import time
from datetime import datetime

# Setup paths
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["FIREBASE_KEY_PATH"] = "backend/serviceAccountKey.json"

from app.db import db

def print_telemetry():
    print("====================================================")
    print("FIRESTORE TELEMETRY DATA")
    print("====================================================")
    
    # 1. config/upstox_status
    doc_ref = db.collection("config").document("upstox_status")
    snap = doc_ref.get()
    if snap.exists:
        data = snap.to_dict()
        print("[*] config/upstox_status:")
        for k, v in sorted(data.items()):
            if "time" in k or "check" in k or "alert" in k:
                # Print as timestamp
                try:
                    ts = float(v)
                    if ts > 0:
                        dt = datetime.fromtimestamp(ts).isoformat()
                        print(f"  - {k}: {v} ({dt})")
                        continue
                except:
                    pass
            print(f"  - {k}: {v}")
    else:
        print("[!] config/upstox_status does not exist")
        
    # 2. live_trading/config
    doc_ref = db.collection("live_trading").document("config")
    snap = doc_ref.get()
    if snap.exists:
        data = snap.to_dict()
        print("\n[*] live_trading/config:")
        for k, v in sorted(data.items()):
            print(f"  - {k}: {v}")
    else:
        print("[!] live_trading/config does not exist")
        
    print("====================================================")

if __name__ == "__main__":
    print_telemetry()
