import logging
import google.generativeai as genai
import json
import time
from typing import Dict, Any, List
from app.config import settings
from app.db import db
from app.agents.explanation import repair_json_text
from app.services.market_regime import determine_market_regime
from app.services.portfolio_health import calculate_portfolio_health_metrics

logger = logging.getLogger(__name__)

# Configure Gemini
genai.configure(api_key=settings.gemini_api_key)

def generate_portfolio_advice(portfolio: Dict[str, Any]) -> Dict[str, Any]:
    """
    Agent 6.5: Portfolio Advisor Agent.
    Runs portfolio health and regime engine checks, drafts Gemini prompt context,
    invokes Gemini to obtain strategic advisor suggestions, and saves outcomes to Firestore.
    """
    logger.info("Portfolio Advisor Agent compiling context...")
    
    # 1. Fetch Health and Regime context
    health = calculate_portfolio_health_metrics(portfolio)
    regime = determine_market_regime()
    div = health.get("diversification_engine", {})
    
    prompt = f"""
    You are an institutional portfolio advisor and risk management officer.
    Analyze the following complete portfolio context:
    
    Portfolio Overview:
    - Overall Health Score: {health.get('overall_health_score')}/100
    - Diversification Score: {health.get('diversification_score')}/100
    - Portfolio Beta: {health.get('portfolio_beta')}
    - Weighted Portfolio Volatility: {health.get('portfolio_volatility')}%
    - Cash Available: ₹{portfolio.get('cash_available'):,.2f} ({health.get('cash_allocation_pct')}% of portfolio)
    - Active holdings positions: {health.get('holdings_count')}
    
    Exposures and Concentrations:
    - Sector Exposures %: {health.get('sector_concentration')}
    - Stock Exposures %: {health.get('stock_concentration')}
    
    Diversification Engine Detection:
    - Overweight Sectors: {div.get('overweight_sectors')}
    - Underweight Sectors: {div.get('underweight_sectors')}
    - Single-Stock Concentrations: {div.get('single_stock_concentration')}
    
    Current Market Regime:
    - Regime Classification: {regime.get('regime')} (Nifty trend: {regime.get('nifty_trend')}, Volatility: {regime.get('volatility_annualized')}%)
    
    Provide your response in raw JSON format exactly matching the following keys:
    - "overall_outlook": "A professional summary of the portfolio health and outlook under the current regime."
    - "top_risks": ["Risk factor 1 from concentration/macro", "Risk factor 2"]
    - "best_opportunities": ["Opportunity 1 from cash/allocation", "Opportunity 2"]
    - "recommended_cash_pct": 15.0, // Suggested cash levels (number)
    - "maximum_exposure_pct": 20.0, // Suggested maximum exposure limit for single stock (number)
    - "sector_advice": "Specific structural sector rotation or allocation advice."
    - "rebalancing_suggestions": ["Rebalance action 1 (e.g. trim overweight)", "Rebalance action 2"]
    - "priority_actions": ["Priority action item 1", "Priority action item 2"]
    
    Return ONLY the raw JSON object. Do not include markdown blocks, comments, or extra text.
    """
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            logger.info(f"Dispatching portfolio advice request to Gemini (Attempt {attempt + 1}/{max_retries})...")
            model = genai.GenerativeModel("gemini-2.5-flash")
            response = model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            
            repaired = repair_json_text(response.text.strip())
            result = json.loads(repaired)
            
            # Map parameters
            advice = {
                "overall_outlook": str(result.get("overall_outlook", "")),
                "top_risks": result.get("top_risks", []),
                "best_opportunities": result.get("best_opportunities", []),
                "recommended_cash_pct": float(result.get("recommended_cash_pct", 15.0)),
                "maximum_exposure_pct": float(result.get("maximum_exposure_pct", 20.0)),
                "sector_advice": str(result.get("sector_advice", "")),
                "rebalancing_suggestions": result.get("rebalancing_suggestions", []),
                "priority_actions": result.get("priority_actions", []),
                "analyzed_at": time.time(),
                "health_summary": health,
                "regime_summary": regime
            }
            
            # Store in Firestore under portfolio_advice collection
            try:
                db.collection("portfolio_advice").document("current").set(advice)
            except Exception as fe:
                logger.error(f"Failed to save portfolio advice in Firestore: {fe}")
                
            return advice
            
        except Exception as e:
            logger.warning(f"Error parsing Gemini portfolio advice on attempt {attempt + 1}: {e}")
            if attempt == max_retries - 1:
                logger.error(f"Gemini portfolio advisor retries exhausted: {e}")
            else:
                time.sleep(1.0)
                
    return get_fallback_portfolio_advice(health, regime)

def get_fallback_portfolio_advice(health: Dict[str, Any], regime: Dict[str, Any]) -> Dict[str, Any]:
    """Returns a default structure on advisor failure."""
    return {
        "overall_outlook": "Portfolio health shows standard allocations under current regime trends.",
        "top_risks": ["Volatility in index sector heavier listings.", "Macro economic index changes."],
        "best_opportunities": ["Optimize cash buffers for dip-buying opportunities.", "Diversify overweight sectors."],
        "recommended_cash_pct": 15.0,
        "maximum_exposure_pct": 20.0,
        "sector_advice": "Maintain balanced sector exposures across active holdings.",
        "rebalancing_suggestions": ["Monitor high exposure holdings relative to safety lines."],
        "priority_actions": ["Review and prune critical risk positions."],
        "analyzed_at": time.time(),
        "health_summary": health,
        "regime_summary": regime
    }
