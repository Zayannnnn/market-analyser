import os
import sys
import logging
from datetime import datetime, timedelta
import json

# Setup paths to ensure local imports resolve
base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(base_dir)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_learning_agent")

from app.db import db
from app.agents.learning_agent import (
    track_predictions,
    evaluate_predictions,
    calculate_and_save_stats,
    optimize_weights,
    send_weekly_report
)

def run_test():
    print("====================================================")
    print("         PHASE 3: LEARNING AGENT INTEGRATION TEST")
    print("====================================================")

    # 1. Clean up old test predictions from prediction_history
    print("[*] Cleaning up old test prediction documents...")
    try:
        docs = db.collection("prediction_history").get()
        deleted_count = 0
        for doc in docs:
            if doc.id.startswith("TEST_"):
                doc.reference.delete()
                deleted_count += 1
        print(f"[+] Deleted {deleted_count} old test prediction documents.")
    except Exception as e:
        print(f"[-] Cleanup failed: {e}")

    # 2. Insert 5 mock historical predictions to allow weight optimization (requires at least 5 docs)
    print("[*] Seeding 5 mock historical predictions for weight optimization...")
    mock_stocks = ["TCS.NS", "RELIANCE.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS"]
    
    # We want to vary the subscores and outcomes to verify that weight optimization responds
    # news_impact, technical_strength, volume_momentum, company_quality
    subscores_list = [
        {"news_sentiment": 80.0, "technical_analysis": 70.0, "growth_potential": 60.0, "fundamentals": 90.0}, # Outperformed Nifty
        {"news_sentiment": 40.0, "technical_analysis": 50.0, "growth_potential": 30.0, "fundamentals": 60.0}, # Underperformed Nifty
        {"news_sentiment": 90.0, "technical_analysis": 80.0, "growth_potential": 85.0, "fundamentals": 75.0}, # Outperformed Nifty
        {"news_sentiment": 30.0, "technical_analysis": 40.0, "growth_potential": 50.0, "fundamentals": 50.0}, # Underperformed Nifty
        {"news_sentiment": 85.0, "technical_analysis": 75.0, "growth_potential": 70.0, "fundamentals": 80.0}, # Outperformed Nifty
    ]
    
    now_utc = datetime.utcnow()
    
    try:
        for i, ticker in enumerate(mock_stocks):
            doc_id = f"TEST_{ticker}_{i}"
            entry_time = (now_utc - timedelta(days=10)).isoformat() + "Z"
            
            # Setup milestone return values
            # Positive returns for high scores (1, 3, 5), negative/lower returns for low scores (2, 4)
            is_winner = (i % 2 == 0)
            stock_ret = 5.5 if is_winner else -2.0
            nifty_ret = 1.2 if is_winner else 1.5
            beat = stock_ret > nifty_ret
            
            prediction_doc = {
                "ticker": ticker,
                "company_name": f"Mock {ticker}",
                "score": int(75 if is_winner else 45),
                "confidence": "High" if is_winner else "Low",
                "entry_price": 1000.0,
                "entry_nifty": 22000.0,
                "entry_time": entry_time,
                "subscores": subscores_list[i],
                "milestones": {
                    "1h": {
                        "evaluated_at": (now_utc - timedelta(days=9)).isoformat() + "Z",
                        "price": 1055.0 if is_winner else 980.0,
                        "nifty": 22264.0 if is_winner else 22330.0,
                        "return": stock_ret,
                        "nifty_return": nifty_ret,
                        "beat": beat
                    },
                    "4h": None,
                    "1d": None,
                    "7d": None,
                    "30d": None
                },
                "status": "active"
            }
            db.collection("prediction_history").document(doc_id).set(prediction_doc)
        print("[+] Seeded 5 mock historical predictions successfully.")
    except Exception as e:
        print(f"[-] Seeding failed: {e}")
        sys.exit(1)

    # 3. Insert 1 mock active prediction that is OVERDUE for the '1h' milestone
    # We use a real active ticker (e.g. RELIANCE.NS) so live price checks resolve correctly
    print("[*] Seeding 1 active prediction overdue for the '1h' milestone...")
    active_ticker = "RELIANCE.NS"
    active_doc_id = f"TEST_ACTIVE_{active_ticker}"
    
    try:
        # Fetch current real entry prices using get_market_data or fallback
        from app.data_sources.market_data import get_market_data
        real_stock_price = 2400.0
        try:
            real_stock_price = float(get_market_data(active_ticker).get("price", 2400.0))
        except Exception as e:
            print(f"[*] Stock price fetch failed, using fallback: {e}")
            
        real_nifty_price = 22000.0
        try:
            real_nifty_price = float(get_market_data("^NSEI").get("price", 22000.0))
        except Exception as e:
            print(f"[*] Nifty price fetch failed, using fallback: {e}")
            
        overdue_entry_time = (now_utc - timedelta(hours=2)).isoformat() + "Z"
        
        active_prediction_doc = {
            "ticker": active_ticker,
            "company_name": f"Mock {active_ticker} Overdue",
            "score": 80,
            "confidence": "High",
            "entry_price": real_stock_price,
            "entry_nifty": real_nifty_price,
            "entry_time": overdue_entry_time,
            "subscores": {"news_sentiment": 80.0, "technical_analysis": 80.0, "growth_potential": 80.0, "fundamentals": 80.0},
            "milestones": {
                "1h": None,
                "4h": None,
                "1d": None,
                "7d": None,
                "30d": None
            },
            "status": "active"
        }
        db.collection("prediction_history").document(active_doc_id).set(active_prediction_doc)
        print(f"[+] Seeded active overdue prediction: {active_ticker} (Entry Price: ₹{real_stock_price}, Nifty: {real_nifty_price})")
    except Exception as e:
        print(f"[-] Seeding active prediction failed: {e}")
        sys.exit(1)

    # 4. Trigger evaluate_predictions() to resolve the overdue '1h' milestone
    print("[*] Triggering evaluate_predictions()...")
    try:
        evaluated = evaluate_predictions()
        print(f"[+] Evaluated predictions count: {len(evaluated)}")
        
        # Check if the active prediction was evaluated
        updated_doc = db.collection("prediction_history").document(active_doc_id).get()
        if updated_doc.exists:
            pred_data = updated_doc.to_dict()
            m_1h = pred_data.get("milestones", {}).get("1h")
            if m_1h is not None:
                print(f"[+] Success! Active prediction milestone '1h' resolved: Return: {m_1h.get('return')}% | Beat Nifty: {m_1h.get('beat')}")
            else:
                print("[-] Failure: Milestone '1h' remains unresolved.")
                sys.exit(1)
        else:
            print("[-] Failure: Active prediction document not found after evaluation.")
            sys.exit(1)
    except Exception as e:
        print(f"[-] Error during evaluate_predictions(): {e}")
        sys.exit(1)

    # 5. Run calculate_and_save_stats() and check if stats doc is updated
    print("[*] Running calculate_and_save_stats()...")
    try:
        stats = calculate_and_save_stats()
        print(f"[+] Current stats: {json.dumps(stats, indent=2)}")
        
        # Verify in Firestore
        db_stats_doc = db.collection("learning_stats").document("current").get()
        if db_stats_doc.exists:
            db_stats = db_stats_doc.to_dict()
            print(f"[+] Firestore verification: Found current stats in DB with win rate {db_stats.get('win_rate')}%")
        else:
            print("[-] Failure: Stats document not found in Firestore.")
            sys.exit(1)
    except Exception as e:
        print(f"[-] Error during calculate_and_save_stats(): {e}")
        sys.exit(1)

    # 6. Run optimize_weights() and check if weights doc is updated
    print("[*] Running optimize_weights()...")
    try:
        weights = optimize_weights()
        print(f"[+] Optimized weights: {json.dumps(weights, indent=2)}")
        
        # Verify in Firestore
        db_weights_doc = db.collection("config").document("weights").get()
        if db_weights_doc.exists:
            db_weights = db_weights_doc.to_dict()
            print(f"[+] Firestore verification: Found config weights in DB: {db_weights}")
        else:
            print("[-] Failure: Weights document not found in Firestore.")
            sys.exit(1)
    except Exception as e:
        print(f"[-] Error during optimize_weights(): {e}")
        sys.exit(1)

    # 7. Run send_weekly_report() to verify Telegram delivery
    print("[*] Testing Telegram Weekly Accuracy Report...")
    try:
        report_sent = send_weekly_report()
        print(f"[+] Weekly report status: {'SENT SUCCESSFULLY' if report_sent else 'FAILED TO SEND / CONFIG MISSING'}")
    except Exception as e:
        print(f"[-] Error sending weekly report: {e}")

    # 8. Test the GET /api/learning/stats FastAPI endpoint using TestClient
    print("[*] Testing GET /api/learning/stats FastAPI endpoint...")
    try:
        from fastapi.testclient import TestClient
        from app.main import app
        
        client = TestClient(app)
        response = client.get("/api/learning/stats")
        print(f"[+] Endpoint status code: {response.status_code}")
        if response.status_code == 200:
            payload = response.json()
            print(f"[+] Endpoint Response: {json.dumps(payload, indent=2)}")
            
            # Assert schema components
            assert "status" in payload, "Missing 'status' in response"
            assert "ai_accuracy" in payload, "Missing 'ai_accuracy' in response"
            assert "active_weights" in payload, "Missing 'active_weights' in response"
            print("[+] Endpoint schema validation: PASSED")
        else:
            print(f"[-] Failure: Endpoint returned {response.status_code}")
            sys.exit(1)
    except Exception as e:
        print(f"[-] Error testing FastAPI endpoint: {e}")
        sys.exit(1)

    # Cleanup the test records
    print("[*] Cleaning up created test prediction documents...")
    try:
        db.collection("prediction_history").document(active_doc_id).delete()
        for i, ticker in enumerate(mock_stocks):
            db.collection("prediction_history").document(f"TEST_{ticker}_{i}").delete()
        print("[+] Cleanup: SUCCESS")
    except Exception as e:
        print(f"[-] Cleanup failed: {e}")

    print("\n====================================================")
    print("LEARNING_AGENT_READY = TRUE")
    print("====================================================")

if __name__ == "__main__":
    run_test()
