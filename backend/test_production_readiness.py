import os
import sys
import time
import json
import logging
from datetime import datetime

# Setup paths to ensure local imports resolve
base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(base_dir)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_production_readiness")

from app.db import db
from app.data_sources.market_data import get_market_data

def run_audit():
    print("====================================================")
    print("          PRODUCTION READINESS AUDIT SUITE")
    print("====================================================")
    
    audit_results = {
        "firestore": {},
        "market_data": {},
        "endpoints": {},
        "env_vars": {}
    }
    
    # 1. Environment Variables Audit
    print("\n[*] Auditing Environment Variables...")
    required_vars = [
        "GEMINI_API_KEY",
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_CHAT_ID",
        "FIREBASE_PROJECT_ID"
    ]
    for var in required_vars:
        val = os.environ.get(var) or ""
        # Check if loaded from .env if missing from os.environ
        if not val:
            try:
                env_path = os.path.join(base_dir, ".env")
                if os.path.exists(env_path):
                    with open(env_path, "r") as f:
                        for line in f:
                            if line.strip() and not line.startswith("#"):
                                parts = line.split("=", 1)
                                if len(parts) == 2 and parts[0].strip() == var:
                                    val = parts[1].strip()
                                    break
            except Exception as e:
                logger.error(f"Error parsing .env file for {var}: {e}")
                
        if not val:
            try:
                from app.config import settings
                if var == "GEMINI_API_KEY": val = settings.gemini_api_key
                elif var == "TELEGRAM_BOT_TOKEN": val = settings.telegram_bot_token
                elif var == "TELEGRAM_CHAT_ID": val = settings.telegram_chat_id
            except:
                pass
        
        status = "CONFIGURED" if val else "MISSING"
        print(f"  - {var}: {status}")
        audit_results["env_vars"][var] = status

    # 2. Firestore Audit (Collections and Write/Read)
    print("\n[*] Auditing Firestore Collections & Connection...")
    collections = ["stocks", "news", "rankings", "snapshots", "ai_analysis", "alerts", "prediction_history", "learning_stats"]
    for col in collections:
        try:
            # Query a single document to verify collection exist/active
            docs = db.collection(col).limit(1).get()
            print(f"  - Collection '{col}': ACCESSIBLE (Contains {len(db.collection(col).get())} docs)")
            audit_results["firestore"][col] = "ACCESSIBLE"
        except Exception as e:
            print(f"  - Collection '{col}': ERROR ({e})")
            audit_results["firestore"][col] = f"ERROR: {e}"

    # 3. Market Data API Audit (Real prices and Benchmarks)
    print("\n[*] Auditing Market Data Feeds (Yahoo Finance HTTP Chart)...")
    tickers = ["RELIANCE.NS", "TCS.NS", "^NSEI"]
    for ticker in tickers:
        try:
            start_time = time.time()
            data = get_market_data(ticker)
            latency = time.time() - start_time
            price = data.get("price", 0.0)
            
            # Check for dummy price
            is_real = (price != 100.0)
            status = "REAL" if is_real else "FALLBACK (₹100)"
            
            print(f"  - Ticker '{ticker}': Price = ₹{price} | Feed = {status} | Latency = {latency:.2f}s")
            audit_results["market_data"][ticker] = {
                "price": price,
                "status": status,
                "latency": latency
            }
        except Exception as e:
            print(f"  - Ticker '{ticker}': ERROR ({e})")
            audit_results["market_data"][ticker] = {"status": f"ERROR: {e}"}

    # 4. FastAPI Endpoints Response Time Audit
    print("\n[*] Auditing FastAPI Endpoints (TestClient)...")
    try:
        from fastapi.testclient import TestClient
        from app.main import app
        client = TestClient(app)
        
        endpoints = [
            "/api/top10",
            "/api/market-summary",
            "/api/alerts",
            "/api/learning/stats"
        ]
        
        for ep in endpoints:
            start_time = time.time()
            response = client.get(ep)
            latency = time.time() - start_time
            
            status = "SUCCESS" if response.status_code == 200 else f"FAILED ({response.status_code})"
            print(f"  - {ep}: {status} | Latency = {latency:.2f}s")
            audit_results["endpoints"][ep] = {
                "status": status,
                "status_code": response.status_code,
                "latency": latency
            }
    except Exception as e:
        print(f"  - FastAPI Endpoint Audit Error: {e}")
        audit_results["endpoints"]["error"] = str(e)
        
    print("\n====================================================")
    print("           PRODUCTION READINESS AUDIT COMPLETE")
    print("====================================================")
    
    # Save audit results to a JSON file for the compiler/report
    with open(os.path.join(base_dir, "audit_results.json"), "w") as f:
        json.dump(audit_results, f, indent=2)

if __name__ == "__main__":
    run_audit()
