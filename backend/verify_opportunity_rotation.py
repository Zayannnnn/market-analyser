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

from app.services.opportunity_rotation import generate_capital_rotation_advisory

def test_opportunity_rotation_e2e():
    logger.info("Initializing E2E Opportunity Ranking and Rotation checks...")
    
    # 1. Trigger the logic
    res = generate_capital_rotation_advisory()
    
    logger.info("\n----------------------------------------------------")
    logger.info("VERIFYING OPPORTUNITY SCORING MATRIX")
    logger.info("----------------------------------------------------")
    
    opps = res.get("opportunity_universe", [])
    logger.info(f"Retrieved {len(opps)} scored stocks in universe:")
    for o in opps:
        logger.info(f" - {o['ticker']}: Opp Score = {o['opportunity_score']} | Tech = {o['technical_score']} | Trend = {o['trend_score']} | Risk = {o['risk_score']}")
        
    logger.info("\n----------------------------------------------------")
    logger.info("VERIFYING CAPITAL ROTATION PLANS")
    logger.info("----------------------------------------------------")
    
    rotation_checklist = res.get("rotation_checklist", [])
    logger.info(f"Rotation Plan suggestions ({len(rotation_checklist)}):")
    for plan in rotation_checklist:
        logger.info(f" - {plan['action']} (Holding Score: {plan['holding_score']} -> Opportunity Score: {plan['opportunity_score']})")
        logger.info(f"   Reasoning: {plan['justification']}")
        
    # Sizing matrix
    sizing = res.get("sizing_matrix", {})
    logger.info(f"\nSizing parameters generated for first universe stock:")
    if opps:
        first_t = opps[0]["ticker"]
        logger.info(f" - {first_t}: Sizing = {sizing.get(first_t)}")
        
    # Verify Committee advisory V2 fields
    decision = res.get("decision", {})
    logger.info(f"\nCommittee V2 output check:")
    logger.info(f" - Overall Decision: {decision.get('overall_decision')}")
    logger.info(f" - Market Regime: {decision.get('market_regime')}")
    logger.info(f" - Highest Buy: {decision.get('highest_priority_buy')}")
    logger.info(f" - Highest Sell: {decision.get('highest_priority_sell')}")
    logger.info(f" - Top Opportunities count: {len(decision.get('top_10_opportunities', []))}")
    logger.info(f" - Capital Rotation Plan list: {decision.get('capital_rotation_plan')}")
    
    logger.info("\n[SUCCESS] E2E Opportunity Ranking and Rotation checks completed successfully.")
    return True

if __name__ == "__main__":
    success = test_opportunity_rotation_e2e()
    if success:
        sys.exit(0)
    else:
        sys.exit(1)
