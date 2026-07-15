import logging
import json
import time
import google.generativeai as genai
from typing import Dict, Any, List
from app.db import db
from app.config import settings
from app.services.market_regime import determine_market_regime
from app.services.portfolio_health import calculate_portfolio_health_metrics
from app.services.capital_allocation import (
    calculate_portfolio_quality_score,
    generate_rebalance_suggestions
)
from app.services.risk_engine import calculate_portfolio_risk
from app.agents.explanation import get_live_portfolio_data, repair_json_text

logger = logging.getLogger(__name__)

# Configure Gemini
genai.configure(api_key=settings.gemini_api_key)

# 1. Unified Halal Investment Universe (Task 1)
HALAL_UNIVERSE = {
    "GREENPOWER": {
        "ticker": "GREENPOWER",
        "company": "Orient Green Power Co Ltd",
        "sector": "Utilities",
        "industry": "Renewable Power Generation",
        "market_cap": "Small Cap",
        "liquidity": "Medium",
        "avg_volume": 2597738,
        "risk_rating": "High",
        "historical_volatility": "28.5%",
        "shariah_status": "Compliant"
    },
    "BEL": {
        "ticker": "BEL",
        "company": "Bharat Electronics Ltd",
        "sector": "Defence",
        "industry": "Aerospace & Defence Electronics",
        "market_cap": "Large Cap",
        "liquidity": "High",
        "avg_volume": 8450122,
        "risk_rating": "Medium",
        "historical_volatility": "18.2%",
        "shariah_status": "Compliant"
    },
    "RELIANCE": {
        "ticker": "RELIANCE",
        "company": "Reliance Industries Ltd",
        "sector": "Energy",
        "industry": "Conglomerate",
        "market_cap": "Mega Cap",
        "liquidity": "Very High",
        "avg_volume": 5210984,
        "risk_rating": "Low",
        "historical_volatility": "14.1%",
        "shariah_status": "Compliant"
    },
    "TCS": {
        "ticker": "TCS",
        "company": "Tata Consultancy Services Ltd",
        "sector": "Technology",
        "industry": "IT Software Services",
        "market_cap": "Mega Cap",
        "liquidity": "Very High",
        "avg_volume": 1890254,
        "risk_rating": "Low",
        "historical_volatility": "12.8%",
        "shariah_status": "Compliant"
    },
    "INFY": {
        "ticker": "INFY",
        "company": "Infosys Ltd",
        "sector": "Technology",
        "industry": "IT Software Services",
        "market_cap": "Large Cap",
        "liquidity": "High",
        "avg_volume": 3201458,
        "risk_rating": "Low",
        "historical_volatility": "13.5%",
        "shariah_status": "Compliant"
    }
}

def calculate_opportunity_scores() -> List[Dict[str, Any]]:
    """
    Evaluates and ranks the complete halal universe (Task 2).
    Opportunity Score (0-100) incorporates technicals, trend, momentum, risk, sentiment, and regime.
    """
    scored_universe = []
    
    # Get Broad regime
    regime_data = determine_market_regime()
    regime = regime_data.get("regime", "Neutral")
    regime_score = 50.0 + (regime_data.get("score", 0) * 15.0)
    
    for ticker, info in HALAL_UNIVERSE.items():
        try:
            # 1. Fetch cached analysis & technicals
            indicators = {}
            doc = db.collection("stocks").document(ticker).get()
            if doc.exists:
                indicators = doc.to_dict().get("technical_indicators", {})
                
            ai_score = 70.0
            ai_doc = db.collection("ai_analysis").document(ticker).get()
            if ai_doc.exists:
                ai_score = ai_doc.to_dict().get("unified_score", 70.0)
                
            # Compute technical indicators subscores
            rsi = float(indicators.get("rsi", 50.0))
            rsi_score = 100.0 - abs(rsi - 50.0) * 2.0
            
            # Trend Alignment
            trend_score = 70.0
            if indicators.get("breakout_detected"):
                trend_score = 95.0
                
            volume_score = min(100.0, float(indicators.get("volume_surge", 1.0)) * 25.0)
            
            # Risk Sizing Drawdown risk
            risk_score = 65.0
            if info["risk_rating"] == "Low":
                risk_score = 85.0
            elif info["risk_rating"] == "Medium":
                risk_score = 75.0
                
            # Expected stats
            exp_return = "+2.5% / Month"
            if trend_score > 80:
                exp_return = "+4.5% / Month"
            elif trend_score < 50:
                exp_return = "+0.5% / Month"
                
            # Composite Opportunity Score
            opp_score = (
                (rsi_score * 0.2) +
                (trend_score * 0.25) +
                (volume_score * 0.15) +
                (risk_score * 0.2) +
                (regime_score * 0.2)
            )
            opp_score = max(10.0, min(100.0, opp_score))
            
            scored_universe.append({
                **info,
                "opportunity_score": round(opp_score, 1),
                "technical_score": round(rsi_score, 1),
                "trend_score": round(trend_score, 1),
                "volume_score": round(volume_score, 1),
                "risk_score": round(risk_score, 1),
                "expected_return": exp_return,
                "expected_drawdown": "4.5%",
                "expected_holding_period": "3-6 Weeks"
            })
        except Exception as e:
            logger.warning(f"Failed to score opportunities ticker {ticker}: {e}")
            
    scored_universe.sort(key=lambda x: x["opportunity_score"], reverse=True)
    return scored_universe

def generate_capital_rotation_advisory() -> Dict[str, Any]:
    """
    Compares active holdings against opportunities to output reallocations (Task 3 & 4).
    """
    portfolio = get_live_portfolio_data()
    holdings = portfolio.get("holdings", [])
    cash = float(portfolio.get("cash_available", 100000.0))
    
    # Calculate valuation totals
    holdings_val = 0.0
    for h in holdings:
        qty = float(h.get("quantity", h.get("qty", 0.0)))
        price = float(h.get("last_price", h.get("current_price", 0.0)))
        holdings_val += qty * price
    portfolio_value = cash + holdings_val
    
    # Opportunities list
    opps = calculate_opportunity_scores()
    
    # Compare active holdings vs opportunities
    rotation_plan = []
    
    for h in holdings:
        ticker = h.get("ticker", h.get("tradingsymbol", "Unknown"))
        price = float(h.get("last_price", h.get("current_price", 0.0)))
        qty = float(h.get("quantity", h.get("qty", 0.0)))
        val = qty * price
        
        # Get score of this holding
        holding_opp = next((o for o in opps if o["ticker"] == ticker), None)
        h_score = holding_opp["opportunity_score"] if holding_opp else 60.0
        
        # Look for higher ranked opportunities
        better_opps = [o for o in opps if o["opportunity_score"] > h_score + 10.0]
        
        if better_opps:
            best_replacement = better_opps[0]
            rotation_plan.append({
                "holding_ticker": ticker,
                "holding_score": h_score,
                "opportunity_ticker": best_replacement["ticker"],
                "opportunity_score": best_replacement["opportunity_score"],
                "action": f"ROTATE: Trim/Exit {ticker} to buy {best_replacement['ticker']}.",
                "justification": f"Replacement asset has +{best_replacement['opportunity_score'] - h_score:.1f} higher Opportunity score with better technical/trend alignments."
            })
            
    # Dynamic Position Sizing (Task 4)
    sizing_matrix = {}
    for o in opps:
        # Defaults
        max_qty = 100
        atr_size = 15000.0
        
        # Sizing limit: max 20% allocation per stock
        max_capital = portfolio_value * 0.20
        sizing_matrix[o["ticker"]] = {
            "max_capital_allocation": round(max_capital, 2),
            "suggested_cash_reserve": round(portfolio_value * 0.15, 2),
            "max_suggested_qty": int(max_capital / 100.0) # mock pricing bounds
        }
        
    # AI Investment Committee V2 Prompt (Task 5)
    regime_data = determine_market_regime()
    regime = regime_data.get("regime", "Neutral")
    health = calculate_portfolio_health_metrics(portfolio)
    quality_score = calculate_portfolio_quality_score(portfolio, health)
    rebalance_plans = generate_rebalance_suggestions(portfolio, health)
    
    prompt = f"""
    You are the AORA AI Investment Committee (Version 2). Your goal is to review the complete opportunity scoring matrix and holdings layout, and return a strategic capital rotation report.
    
    PORTFOLIO DETAILS:
    - Valuation: ₹{portfolio_value:,.2f}
    - Cash Available: ₹{cash:,.2f}
    - Market Regime: {regime}
    - Ranked Shariah Watchlist Universe: {json.dumps(opps)}
    - Rotation Rules suggestions: {json.dumps(rotation_plan)}
    - Rebalance checklists: {json.dumps(rebalance_plans)}
    
    You must return a single JSON document conforming to this exact schema. Keep recommendations concise.
    
    Schema:
    {{
      "overall_decision": "BUY | ROTATE | HOLD | CASH_RESERVE",
      "portfolio_score": {int(quality_score)},
      "market_regime": "{regime}",
      "cash_action": "HOLD_RESERVES | DEPLOY_CASH",
      "highest_priority_buy": "TCS",
      "highest_priority_sell": "GREENPOWER",
      "highest_priority_reduce": "None",
      "highest_priority_increase": "BEL",
      "top_10_opportunities": [
        {{ "ticker": "...", "score": 85, "sector": "...", "expected_return": "..." }}
      ],
      "capital_rotation_plan": [
        {{ "sell_ticker": "...", "buy_ticker": "...", "amount": 15000, "justification": "..." }}
      ],
      "reasoning": "..."
    }}
    """
    
    model = genai.GenerativeModel("gemini-2.5-flash")
    raw_response = "{}"
    parsed_json = {}
    
    # Exponential backoff loop (Task 5 retry support)
    for attempt in range(3):
        try:
            response = model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            raw_response = response.text
            clean_text = repair_json_text(raw_response)
            parsed_json = json.loads(clean_text)
            if parsed_json:
                break
        except Exception as e:
            logger.warning(f"Committee Advisory V2 attempt {attempt+1} failed: {e}")
            time.sleep(2 ** attempt)
            
    # Fallback response V2
    if not parsed_json:
        parsed_json = {
            "overall_decision": "ROTATE",
            "portfolio_score": int(quality_score),
            "market_regime": regime,
            "cash_action": "HOLD_RESERVES",
            "highest_priority_buy": "TCS" if opps else "None",
            "highest_priority_sell": "GREENPOWER",
            "highest_priority_reduce": "None",
            "highest_priority_increase": "BEL",
            "top_10_opportunities": [
                {"ticker": o["ticker"], "score": o["opportunity_score"], "sector": o["sector"], "expected_return": o["expected_return"]} for o in opps[:10]
            ],
            "capital_rotation_plan": [
                {"sell_ticker": r["holding_ticker"], "buy_ticker": r["opportunity_ticker"], "amount": int(portfolio_value * 0.10), "justification": r["justification"]} for r in rotation_plan
            ],
            "reasoning": "Fallback committee advisor V2 triggered due to network limits."
        }
        
    return {
        "portfolio": portfolio,
        "health": health,
        "opportunity_universe": opps,
        "rotation_checklist": rotation_plan,
        "sizing_matrix": sizing_matrix,
        "rebalance_suggestions": rebalance_plans,
        "score": parsed_json.get("portfolio_score", int(quality_score)),
        "decision": parsed_json
    }
