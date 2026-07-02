import os
import sys
import logging
from datetime import datetime

# Setup paths to ensure local imports resolve
base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(base_dir)

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("test_firestore")

def run_verification():
    print("====================================================")
    print("   FIREBASE FIRESTORE CONNECTION VERIFICATION")
    print("====================================================")
    
    # 1. Test key file path
    service_key_path = os.path.join(base_dir, "serviceAccountKey.json")
    if not os.path.exists(service_key_path):
        print(f"[-] Key file check: FAILED. File not found at {service_key_path}")
        sys.exit(1)
    print(f"[+] Key file check: SUCCESS (Located at: {service_key_path})")

    # 2. Test initialization
    try:
        from app.db import db, MockFirestoreClient
        if isinstance(db, MockFirestoreClient):
            print("[-] Firebase Admin initialization: FAILED (Fallback Mock client loaded instead).")
            print("    Please check if serviceAccountKey.json is a valid Firebase credentials file.")
            sys.exit(1)
        print("[+] Firebase Admin initialization: SUCCESS")
    except Exception as e:
        print(f"[-] Firebase Admin initialization: FAILED. Error: {e}")
        sys.exit(1)

    # 3. Resolve Project ID
    project_id = "Unknown"
    try:
        project_id = db.project
        print(f"[+] Firebase Project ID detected: {project_id}")
    except Exception as e:
        print(f"[-] Firebase Project ID detection: WARNING. Error: {e}")

    # 4. Perform Firestore write
    try:
        current_time = datetime.utcnow().isoformat() + "Z"
        doc_ref = db.collection("test_connection").document("verification_doc")
        
        test_payload = {
            "status": "connected",
            "timestamp": current_time
        }
        
        print("[*] Attempting Firestore document WRITE...")
        doc_ref.set(test_payload)
        print("[+] Firestore document WRITE: SUCCESS")
    except Exception as e:
        print(f"[-] Firestore document WRITE: FAILED. Error: {e}")
        sys.exit(1)

    # 5. Perform Firestore read
    try:
        print("[*] Attempting Firestore document READ...")
        snapshot = doc_ref.get()
        if not snapshot.exists:
            print("[-] Firestore document READ: FAILED. Document write completed but not found on read.")
            sys.exit(1)
            
        read_payload = snapshot.to_dict()
        print(f"[+] Firestore document READ: SUCCESS (Payload: {read_payload})")
    except Exception as e:
        print(f"[-] Firestore document READ: FAILED. Error: {e}")
        sys.exit(1)

    # 6. Verify payload matching
    if read_payload.get("status") == "connected" and read_payload.get("timestamp") == current_time:
        print("[+] Payload Verification: SUCCESS (Matches written parameters)")
        print("====================================================")
        print("VERIFICATION RESULT: FIREBASE FIRESTORE ONLINE & FULLY STABLE!")
        print("====================================================")
        
        # Clean up
        try:
            doc_ref.delete()
            print("[+] Connection logs cleanup: SUCCESS")
        except Exception as e:
            print(f"[-] Connection logs cleanup: WARNING. Error: {e}")
            
        sys.exit(0)
    else:
        print("[-] Payload Verification: FAILED (Read payload values did not match written variables)")
        print(f"    Written: {test_payload}")
        print(f"    Read: {read_payload}")
        sys.exit(1)

if __name__ == "__main__":
    run_verification()
