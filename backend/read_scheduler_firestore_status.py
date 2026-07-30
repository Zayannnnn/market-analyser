import os
import sys
from datetime import datetime

# Setup paths
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["FIREBASE_KEY_PATH"] = "backend/serviceAccountKey.json"

from app.db import db

def print_scheduler_firestore_status():
    print("====================================================")
    print("FIRESTORE SCHEDULER telemetry STATUS")
    print("====================================================")
    
    # 1. Fetch document paper_scheduler/status
    doc_ref = db.collection("paper_scheduler").document("status")
    doc = doc_ref.get()
    
    if doc.exists:
        data = doc.to_dict()
        print("[*] Document 'paper_scheduler/status' exists:")
        for k, v in sorted(data.items()):
            if k == "logs":
                print(f"  - logs count: {len(v)}")
                # Show last 5 log entries
                print("    Last 5 logs:")
                for entry in v[-5:]:
                    print(f"      * {entry}")
            else:
                print(f"  - {k}: {v}")
    else:
        print("[!] Document 'paper_scheduler/status' does NOT exist")
        
    print()
    # 2. Let's list any other collections in paper_scheduler if they exist
    print("[*] Fetching other collections / documents...")
    # Read status logs
    docs = db.collection("paper_scheduler").list_documents()
    for d in docs:
        if d.id != "status":
            print(f"  - Document ID: {d.id} -> {d.get().to_dict()}")
            
    print("====================================================")

if __name__ == "__main__":
    print_scheduler_firestore_status()
