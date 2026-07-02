import os
import sys
import json
import logging

base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(base_dir)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_endpoints")

from fastapi.testclient import TestClient
from app.main import app

def run_tests():
    client = TestClient(app)
    
    print("====================================================")
    print("        VERIFYING NEW BACKEND ENDPOINTS")
    print("====================================================")
    
    # 1. Test /api/stocks/RELIANCE
    print("\n[*] Testing GET /api/stocks/RELIANCE...")
    res = client.get("/api/stocks/RELIANCE")
    if res.status_code == 200:
        data = res.json()
        print("[+] GET /api/stocks/RELIANCE: SUCCESS")
        print(f"  - Ticker: {data.get('ticker')}")
        print(f"  - Company Name: {data.get('company_name')}")
        print(f"  - Price: {data.get('price')}")
        print(f"  - Support: ₹{data.get('support')}")
        print(f"  - Resistance: ₹{data.get('resistance')}")
        print(f"  - Rec: {data.get('recommendation')}")
        print(f"  - Valuation Score: {data.get('valuation_score')}")
        print(f"  - Growth Score: {data.get('growth_score')}")
        print(f"  - Risk Score: {data.get('risk_score')}")
        print(f"  - Is Halal: {data.get('is_halal')}")
        print(f"  - News count: {len(data.get('news', []))}")
        print(f"  - History length: {len(data.get('history_close', []))}")
    else:
        print(f"[-] GET /api/stocks/RELIANCE: FAILED (Status: {res.status_code}, Body: {res.text})")

    # 2. Test /api/learning/daily-close-report
    print("\n[*] Testing POST /api/learning/daily-close-report...")
    res_report = client.post("/api/learning/daily-close-report")
    if res_report.status_code == 200:
        print("[+] POST /api/learning/daily-close-report: SUCCESS")
        print(f"  - Response: {res_report.json()}")
    else:
        print(f"[-] POST /api/learning/daily-close-report: FAILED (Status: {res_report.status_code}, Body: {res_report.text})")

    print("\n====================================================")
    print("             VERIFICATION COMPLETE")
    print("====================================================")

if __name__ == "__main__":
    run_tests()
