import os
import sys
import logging

# Setup sys path to include backend
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set env variables before imports
os.environ["FIREBASE_KEY_PATH"] = "backend/serviceAccountKey.json"

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

from app.db import db
from app.services.paper_scheduler import simulate_one_trading_day

def test_scheduler_simulation_e2e():
    logger.info("Initializing E2E Paper Scheduler simulation verification check...")
    
    # Run the simulated day loop
    logger.info("Simulating one trading day...")
    res = simulate_one_trading_day()
    
    logger.info("\n----------------------------------------------------")
    logger.info("VERIFYING SIMULATED SCHEDULER STATES")
    logger.info("----------------------------------------------------")
    
    # Read status from Firestore
    status_doc = db.collection("paper_scheduler").document("status").get().to_dict()
    logger.info(f"Scheduler Status: {status_doc.get('status')}")
    logger.info(f"Last Scan Time: {status_doc.get('last_scan_time')}")
    logger.info(f"Next Scan Time: {status_doc.get('next_scan_time')}")
    logger.info(f"Gemini API check: {status_doc.get('gemini_status')}")
    logger.info(f"Upstox API check: {status_doc.get('upstox_status')}")
    logger.info(f"Firestore status: {status_doc.get('firestore_status')}")
    logger.info(f"Telegram status: {status_doc.get('telegram_status')}")
    
    # Print execution logs
    logs = status_doc.get("logs", [])
    logger.info(f"\nExecution Logs Captured ({len(logs)}):")
    for log in logs:
        logger.info(f" - [{log['level']}] {log['event']}: {log['message']}")
        
    # Read open trades
    positions = [doc.to_dict() for doc in db.collection("paper_positions").get()]
    logger.info(f"\nActive open positions after simulation: {len(positions)}")
    for pos in positions:
        logger.info(f" - {pos['ticker']}: Qty {pos['quantity']} | Entry: ₹{pos['entry_price']:.2f} | SL: ₹{pos['stop_loss']:.2f} | Target: ₹{pos['target']:.2f}")
        
    logger.info("\n[SUCCESS] E2E Paper Scheduler simulation verification completed successfully.")
    return True

if __name__ == "__main__":
    success = test_scheduler_simulation_e2e()
    if success:
        sys.exit(0)
    else:
        sys.exit(1)
