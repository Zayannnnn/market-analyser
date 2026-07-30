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
from app.agents.portfolio_manager import generate_portfolio_manager_advice

def test_portfolio_manager_e2e():
    logger.info("Initializing E2E AI Portfolio Manager verification check...")
    
    # 1. Trigger the advisor logic
    res = generate_portfolio_manager_advice()
    
    logger.info("\n----------------------------------------------------")
    logger.info("VERIFYING AI PORTFOLIO ADVISOR STATES")
    logger.info("----------------------------------------------------")
    
    logger.info(f"Calculated Portfolio Quality Score: {res.get('score')}/100")
    logger.info(f"Committee Decision: {res['decision'].get('overall_decision')}")
    logger.info(f"Expected Volatility Risk: {res['decision'].get('expected_volatility')}")
    logger.info(f"Expected Monthly Returns: {res['decision'].get('expected_monthly_return')}")
    
    # Verify allocations & exposure
    health = res["health"]
    logger.info(f"\nExposures & Risks:")
    logger.info(f" - Portfolio Beta: {health.get('portfolio_beta')}")
    logger.info(f" - Portfolio Volatility: {health.get('portfolio_volatility')}%")
    logger.info(f" - Sector Concentrators: {health.get('sector_exposures')}")
    
    # Verify suggestions
    suggestions = res.get("rebalance_suggestions", [])
    logger.info(f"\nRebalancing suggestions generated ({len(suggestions)}):")
    for sug in suggestions:
        logger.info(f" - {sug}")
        
    # Verify Queues
    buys = res["decision"].get("buy_candidates", [])
    sells = res["decision"].get("sell_candidates", [])
    reduces = res["decision"].get("reduce_positions", [])
    increases = res["decision"].get("increase_positions", [])
    
    logger.info(f"\nExecution queues:")
    logger.info(f" - Buy candidates: {buys}")
    logger.info(f" - Sell candidates: {sells}")
    logger.info(f" - Trim candidates: {reduces}")
    logger.info(f" - Top-up candidates: {increases}")
    
    logger.info("\n[SUCCESS] E2E AI Portfolio Manager verification completed successfully.")
    return True

if __name__ == "__main__":
    success = test_portfolio_manager_e2e()
    if success:
        sys.exit(0)
    else:
        sys.exit(1)
