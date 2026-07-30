import os
import sys
from datetime import datetime

# Setup paths
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["FIREBASE_KEY_PATH"] = "backend/serviceAccountKey.json"

from app.db import db

def print_rankings_telemetry():
    print("====================================================")
    print("FIRESTORE RANKINGS TELEMETRY AUDIT")
    print("====================================================")
    
    # 1. Check last document in rankings collection
    # Firebase Firestore orders collections
    try:
        rankings_ref = db.collection("rankings")
        # Query and order by timestamp descending
        docs = list(rankings_ref.order_by("timestamp", direction="DESCENDING").limit(5).stream())
        if docs:
            print("[*] Found recent rankings documents:")
            for d in docs:
                data = d.to_dict()
                print(f"  - Document ID: {d.id}")
                print(f"    Timestamp: {data.get('timestamp')}")
                print(f"    Stocks count: {len(data.get('rankings', []))}")
        else:
            print("[!] No documents found in rankings collection.")
    except Exception as e:
        print(f"[!] Error reading rankings collection: {e}")
        
    print()
    # 2. Check top10 document update time
    try:
        top10_ref = db.collection("rankings").document("top10")
        snap = top10_ref.get()
        if snap.exists:
            data = snap.to_dict()
            print("[*] rankings/top10 document:")
            print(f"  - updated_at: {data.get('updated_at') or data.get('timestamp')}")
        else:
            print("[!] rankings/top10 document does not exist.")
    except Exception as e:
        print(f"[!] Error reading rankings/top10: {e}")
        
    print("====================================================")

if __name__ == "__main__":
    print_rankings_telemetry()
