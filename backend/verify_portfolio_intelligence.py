import os
import sys
import logging
import json

# Setup sys path to include backend
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set env variables before imports
os.environ["FIREBASE_KEY_PATH"] = "backend/serviceAccountKey.json"

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

from app.db import db
from app.agents.explanation import get_live_portfolio_data
from app.services.portfolio_health import calculate_portfolio_health_metrics
from app.agents.portfolio_advisor import generate_portfolio_advice

def test_portfolio_intelligence():
    logger.info("Initializing Portfolio Intelligence E2E Verification Check...")
    
    # 1. Fetch live portfolio data from Firestore / Upstox
    logger.info("Fetching live portfolio details...")
    try:
        portfolio = get_live_portfolio_data()
        logger.info(f"Successfully retrieved portfolio. Cash Available: Rs. {portfolio.get('cash_available')}")
        logger.info(f"Holdings positions count: {len(portfolio.get('holdings', []))}")
    except Exception as e:
        logger.error(f"Error fetching portfolio details: {e}")
        return False

    # 2. Run Portfolio Health Engine
    logger.info("Running Portfolio Health Engine indicators...")
    try:
        health = calculate_portfolio_health_metrics(portfolio)
        logger.info("\n==============================================")
        logger.info("PORTFOLIO HEALTH RESULTS:")
        logger.info(f"Overall Health Score: {health['overall_health_score']}/100")
        logger.info(f"Diversification Score: {health['diversification_score']}/100")
        logger.info(f"Portfolio Beta: {health['portfolio_beta']}")
        logger.info(f"Weighted Volatility: {health['portfolio_volatility']}%")
        logger.info(f"Cash Allocation: {health['cash_allocation_pct']}%")
        logger.info(f"Risk Rating: {health['risk_rating']}")
        logger.info(f"Holdings Count: {health['holdings_count']}")
        logger.info("==============================================\n")
    except Exception as e:
        logger.error(f"Error executing health engine: {e}", exc_info=True)
        return False

    # 3. Verify Diversification Engine
    logger.info("Verifying Diversification Engine warnings...")
    div = health.get("diversification_engine", {})
    logger.info(f"Overweight Sectors: {div.get('overweight_sectors')}")
    logger.info(f"Underweight Sectors: {div.get('underweight_sectors')}")
    logger.info(f"Single-Stock Concentration Tickers: {div.get('single_stock_concentration')}")
    logger.info(f"Holdings concentration HHI index: {div.get('hhi_stock')}")

    # 4. Verify AI Advisor Agent
    logger.info("Triggering Gemini AI Portfolio Advisor...")
    try:
        advice = generate_portfolio_advice(portfolio)
        logger.info("\n==============================================")
        logger.info("AI PORTFOLIO ADVISOR RESPONSE:")
        logger.info(f"Overall Outlook:\n{advice['overall_outlook']}")
        logger.info(f"Recommended Cash Ratio: {advice['recommended_cash_pct']}%")
        logger.info(f"Max Position Cap Limit: {advice['maximum_exposure_pct']}%")
        logger.info(f"Sector Rotation Advice:\n{advice['sector_advice']}")
        logger.info(f"Rebalancing Suggestions: {advice['rebalancing_suggestions']}")
        logger.info(f"Priority Actions: {advice['priority_actions']}")
        logger.info("==============================================\n")
    except Exception as e:
        logger.error(f"Error calling AI advisor: {e}", exc_info=True)
        return False

    return True

if __name__ == "__main__":
    success = test_portfolio_intelligence()
    if success:
        logger.info("[SUCCESS] Portfolio intelligence verification passed completely.")
        sys.exit(0)
    else:
        logger.error("[FAILURE] Portfolio verification failed.")
        sys.exit(1)
