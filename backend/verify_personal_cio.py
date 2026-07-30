import os
import sys
import time
import pandas as pd
import logging

# Setup sys path to include backend
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set env variables before imports
os.environ["FIREBASE_KEY_PATH"] = "backend/serviceAccountKey.json"

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

from app.services.decision_quality import run_decision_quality_committee, find_historical_matches
from app.services.macro_engine import run_macro_committee_evaluation, determine_market_health
from app.services.learning_engine import record_trade_outcome, calculate_stock_reliability
from app.db import db

def test_personal_cio_decision_quality_e2e():
    logger.info("Initializing E2E Personal CIO and Decision Quality Engine checks...")
    
    # 1. Verify Macro Engine outputs
    logger.info("Verifying Macro health & institutional money flows engines...")
    health = determine_market_health()
    logger.info(f" - Market Health Status: {health['health_status']}")
    assert health["health_status"] in ["Strong Bull", "Bull", "Neutral", "Bear", "Strong Bear"]
    
    macro_eval = run_macro_committee_evaluation()
    logger.info(f" - Macro Committee Vote: {macro_eval['vote']} | Reason: {macro_eval['reason']}")
    assert macro_eval["vote"] in ["BUY", "HOLD", "SELL", "WAIT"]

    # 2. Verify Historical Similarity Match Calculations
    logger.info("Verifying Historical Similarity setups search...")
    stock_doc = db.collection("stocks").document("BEL").get()
    if stock_doc.exists:
        stock_data = stock_doc.to_dict()
    else:
        stock_data = {
            "ticker": "BEL",
            "current_price": 320.0,
            "technical_indicators": {"rsi": 42.0, "macd": 2.50}
        }
        
    # Generate mock daily closes dataframe to check matches calculations
    dates = pd.date_range(end="2026-07-05", periods=100)
    closes = [300.0 + i*0.5 for i in range(100)]
    highs = [c * 1.01 for c in closes]
    lows = [c * 0.99 for c in closes]
    volumes = [2000000 for _ in range(100)]
    df = pd.DataFrame({"close": closes, "high": highs, "low": lows, "volume": volumes}, index=dates)
    
    similarity = find_historical_matches(
        "BEL", 
        {"rsi": 42.0, "macd": 2.50, "ema20": 310.0, "ema50": 305.0}, 
        df
    )
    logger.info(f" - Historical Similarity win rate: {similarity['historical_win_rate']}% | Matches: {similarity['historical_matches']}")
    assert similarity["historical_win_rate"] >= 0.0
    
    # 3. Verify Multi-Stage Committee Consensus & Confidence Gating
    logger.info("Executing 7-Stage Committee Consensus votes analysis...")
    decision = run_decision_quality_committee("BEL", stock_data, df)
    logger.info(f" - Consensus Action: {decision['action']} | Confidence: {decision['confidence']}%")
    logger.info(f" - Committee Votes: {decision['committee_votes']}")
    assert decision["action"] in ["WAIT", "WATCH", "BUY", "HIGH CONVICTION BUY", "SELL", "HOLD"]
    
    # 4. Verify Weight Optimizer Rolling updates
    logger.info("Testing Weight Optimizer self-learning step...")
    # Initial weights check
    w_ref = db.collection("config").document("committee_weights")
    initial_w = w_ref.get().to_dict() if w_ref.get().exists else None
    
    # Simulate a WIN outcome to optimize weights
    trade_data = {
        "entry_price": 300.0,
        "exit_price": 330.0,
        "holding_period": 4,
        "committee_votes": {
            "Technical": "BUY", "News": "BUY", "Regime": "BUY", "Risk": "HOLD",
            "Portfolio": "HOLD", "Historical": "BUY", "Macro": "BUY"
        }
    }
    record_trade_outcome("BEL", trade_data)
    
    optimized_w = w_ref.get().to_dict()
    logger.info(f" - Optimized Committee Weights: {optimized_w}")
    assert optimized_w is not None
    
    # Restore initial weights if existed to maintain state
    if initial_w:
        w_ref.set(initial_w)
        
    # 5. Verify Stock Reliability Grading
    logger.info("Verifying Stock Reliability Score calculations...")
    grade = calculate_stock_reliability("BEL", {"win_rate": 82.5, "avg_return": 6.8, "max_drawdown": 1.5})
    logger.info(f" - Reliability Grade for BEL: {grade}")
    assert grade in ["A+", "A", "B", "C", "Avoid"]
    
    # Compile Morning Brief details
    from app.services.personal_cio import generate_morning_cio_brief
    logger.info("Generating Morning CIO 4-Question Brief Report...")
    brief = generate_morning_cio_brief()
    logger.info("\n----------------------------------------------------")
    logger.info("AORA PERSONAL CIO REPORT")
    logger.info("----------------------------------------------------")
    logger.info(f"1. What to Buy: {[b['ticker'] for b in brief['q1_what_to_buy']]}")
    logger.info(f"2. What to Sell: {[s['ticker'] for s in brief['q2_what_to_sell']]}")
    logger.info(f"3. Suggested Investment: Rs. {brief['q3_how_much_to_invest']:.2f}")
    logger.info(f"4. Committee 'Why' Reason: {brief['q4_why'][:120]}...")
    logger.info("----------------------------------------------------")
    
    logger.info("\n[SUCCESS] Personal CIO & Decision Quality checks completed successfully.")
    return True

if __name__ == "__main__":
    success = test_personal_cio_decision_quality_e2e()
    if success:
        sys.exit(0)
    else:
        sys.exit(1)
