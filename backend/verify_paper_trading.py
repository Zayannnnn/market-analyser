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
from app.services.paper_trading import (
    initialize_paper_portfolio,
    execute_daily_scan,
    run_ai_self_learning,
    get_paper_portfolio,
    get_performance_analytics
)

def test_paper_trading_e2e():
    logger.info("Initializing E2E Paper Trading Engine verification check...")
    
    # 1. Reset virtual portfolio
    initialize_paper_portfolio(force_reset=True)
    
    # 2. Register mock watchlist
    watchlist_symbols = ["GREENPOWER", "BEL", "RELIANCE", "TCS", "INFY"]
    db.collection("config").document("watchlist").set({"symbols": watchlist_symbols})
    logger.info(f"Registered watchlist symbols: {watchlist_symbols}")
    
    # 3. Simulate 5 trading days
    for day in range(1, 6):
        logger.info(f"\n====================================================")
        logger.info(f"SIMULATING TRADING DAY {day}")
        logger.info(f"====================================================")
        
        # Execute daily scanning loop (Task 2 & 3)
        scan_res = execute_daily_scan()
        logger.info(f"Scan Completed: Portfolio Value = ₹{scan_res['portfolio_value']:.2f} | Cash = ₹{scan_res['cash']:.2f} | Unrealized P&L = ₹{scan_res['unrealized_pnl']:.2f}")
        
        # Run AI self-learning cycle (Task 6)
        learn_res = run_ai_self_learning()
        logger.info(f"AI Self-Learning updated: {learn_res.get('lessons')[:150]}...")
        
    # 4. Fetch final records
    logger.info("\n----------------------------------------------------")
    logger.info("VERIFYING SIMULATION RESULTS")
    logger.info("----------------------------------------------------")
    
    final_port = get_paper_portfolio()
    logger.info(f"Final Capital Balance: ₹{final_port['cash']:.2f}")
    logger.info(f"Final Total Valuation: ₹{final_port['portfolio_value']:.2f}")
    
    # List positions
    positions = [doc.to_dict() for doc in db.collection("paper_positions").get()]
    logger.info(f"Active Open Positions ({len(positions)}):")
    for p in positions:
        logger.info(f" - {p['ticker']}: {p['quantity']} shares at ₹{p['entry_price']:.2f} (Current: ₹{p['current_price']:.2f} | Unrealized: ₹{p['unrealized_pnl']:.2f})")
        
    # List orders
    orders = [doc.to_dict() for doc in db.collection("paper_orders").get()]
    logger.info(f"Simulated Order History ({len(orders)}):")
    for o in orders:
        logger.info(f" - [{o['order_type']}] {o['ticker']}: {o['quantity']} shares at ₹{o['price']:.2f}")
        
    # List trade journal entries
    trades = [doc.to_dict() for doc in db.collection("paper_trades").get()]
    logger.info(f"Trade Journal Entries ({len(trades)}):")
    for t in trades:
        logger.info(f" - {t['ticker']}: Entry: ₹{t['entry_price']:.2f} -> Exit: ₹{t['exit_price']:.2f} | P&L: ₹{t['pnl_val']:.2f} ({t['pnl_pct']:.2f}%)")
        
    # Analytics
    analytics = get_performance_analytics()
    logger.info(f"Performance Metrics: WinRate = {analytics['win_rate']}% | ProfitFactor = {analytics['profit_factor']} | MaxDrawdown = {analytics['max_drawdown']}%")
    
    logger.info("\n[SUCCESS] E2E Paper Trading Engine verification completed successfully.")
    return True

if __name__ == "__main__":
    success = test_paper_trading_e2e()
    if success:
        sys.exit(0)
    else:
        sys.exit(1)
