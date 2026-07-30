import os
import sys

# Setup paths
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["FIREBASE_KEY_PATH"] = "backend/serviceAccountKey.json"

from app.db import db

def mask_token(token):
    if not token or len(token) < 10:
        return "None/Empty"
    return token[:6] + "..." + token[-6:]

def read_auth_docs():
    print("====================================================")
    print("FIRESTORE AUTHENTICATION DOCUMENTS CHECK")
    print("====================================================")
    
    # 1. Check config/upstox
    doc_upstox = db.collection("config").document("upstox").get()
    if doc_upstox.exists:
        data = doc_upstox.to_dict()
        print("[*] config/upstox document:")
        for k, v in data.items():
            val = mask_token(v) if "token" in k or "accessToken" in k else v
            print(f"  - {k}: {val}")
    else:
        print("[!] config/upstox document does NOT exist")
        
    print()
    # 2. Check config/upstox_auth
    doc_auth = db.collection("config").document("upstox_auth").get()
    if doc_auth.exists:
        data = doc_auth.to_dict()
        print("[*] config/upstox_auth document:")
        for k, v in data.items():
            val = mask_token(v) if "token" in k or "accessToken" in k else v
            print(f"  - {k}: {val}")
    else:
        print("[!] config/upstox_auth document does NOT exist")
        
    print()
    # 3. Check config/upstox_status
    doc_status = db.collection("config").document("upstox_status").get()
    if doc_status.exists:
        data = doc_status.to_dict()
        print("[*] config/upstox_status document:")
        for k, v in data.items():
            print(f"  - {k}: {v}")
    else:
        print("[!] config/upstox_status document does NOT exist")
    print("====================================================")

if __name__ == "__main__":
    read_auth_docs()
