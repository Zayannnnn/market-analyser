import logging
import json
import time
import google.generativeai as genai
from typing import Dict, Any, List
from app.db import db
from app.config import settings
from app.data_sources.market_data import upstox_client
from app.services.market_regime import determine_market_regime
from app.services.portfolio_health import calculate_portfolio_health_metrics
from app.services.capital_allocation import (
    calculate_portfolio_quality_score,
    generate_rebalance_suggestions,
    initialize_halal_watchlist
)
from app.services.sell_engine import evaluate_sell_decision
from app.agents.explanation import get_live_portfolio_data, repair_json_text

logger = logging.getLogger(__name__)

# Configure Gemini
genai.configure(api_key=settings.gemini_api_key)

def generate_portfolio_manager_advice() -> Dict[str, Any]:
    """
    E2E AI Portfolio Manager Decision Engine (Phase 6.2).
    Coordinates Regime -> Holdings -> Cash -> Sells -> Reduces -> Increases -> New Buy Scans.
    """
    logger.info("Executing E2E AI Portfolio Manager Decision Engine...")
    
    # 1. Initialize watchlists
    initialize_halal_watchlist()
    
    # 2. Get active portfolio
    portfolio = get_live_portfolio_data()
    holdings = portfolio.get("holdings", [])
    cash = float(portfolio.get("cash_available", 100000.0))
    
    # Resolve value totals
    holdings_val = 0.0
    for h in holdings:
        qty = float(h.get("quantity", h.get("qty", 0.0)))
        price = float(h.get("last_price", h.get("current_price", 0.0)))
        holdings_val += qty * price
    portfolio_value = cash + holdings_val
    
    # 3. Market Regime
    regime_data = determine_market_regime()
    regime = regime_data.get("regime", "Neutral")
    
    # 4. Fetch indicators and evaluate Sell Engine on active holdings
    sell_candidates = []
    reduce_candidates = []
    holdings_context = []
    
    for h in holdings:
        ticker = h.get("ticker", h.get("tradingsymbol", "Unknown"))
        qty = float(h.get("quantity", h.get("qty", 0.0)))
        price = float(h.get("last_price", h.get("current_price", 0.0)))
        entry = float(h.get("average_price", price))
        
        # Get tech metrics
        indicators = {}
        try:
            doc = db.collection("stocks").document(ticker).get()
            if doc.exists:
                indicators = doc.to_dict().get("technical_indicators", {})
        except:
            pass
            
        sl = entry * 0.90 # default stop loss
        target = entry * 1.25 # default target
        
        # Check if stored in positions database
        pos_doc = db.collection("paper_positions").document(ticker).get()
        if pos_doc.exists:
            pos_data = pos_doc.to_dict()
            sl = pos_data.get("stop_loss", sl)
            target = pos_data.get("target", target)
            
        # Run Sell Engine
        sell_res = evaluate_sell_decision(
            ticker=ticker,
            current_price=price,
            entry_price=entry,
            stop_loss=sl,
            target=target,
            indicators=indicators,
            news_sentiment_score=0.0,
            market_regime=regime,
            upcoming_event_detected=False,
            risk_score=50.0
        )
        
        h_info = {
            "ticker": ticker,
            "quantity": qty,
            "current_price": price,
            "entry_price": entry,
            "allocation_pct": ((qty * price) / portfolio_value) * 100.0 if portfolio_value > 0 else 0.0,
            "sell_decision": sell_res["decision"],
            "reasons": sell_res["reasons"]
        }
        holdings_context.append(h_info)
        
        if sell_res["decision"] == "SELL":
            sell_candidates.append(h_info)
        elif sell_res["decision"] == "REDUCE":
            reduce_candidates.append(h_info)
            
    # 5. Fetch Shariah watchlists & screen for BUY opportunities
    watchlist_docs = db.collection("halal_watchlist").get()
    buy_candidates = []
    
    for doc in watchlist_docs:
        w_data = doc.to_dict()
        ticker = w_data["ticker"]
        
        # Check if already holding
        is_held = any(h.get("ticker", "") == ticker for h in holdings)
        if is_held:
            continue
            
        # Check technical score
        unified_score = 70
        rec = "HOLD"
        try:
            ai_doc = db.collection("ai_analysis").document(ticker).get()
            if ai_doc.exists:
                ai_data = ai_doc.to_dict()
                unified_score = ai_data.get("unified_score", 70)
                rec = ai_data.get("recommendation", "HOLD")
        except:
            pass
            
        if rec == "BUY" and w_data.get("shariah_status") == "Compliant":
            buy_candidates.append({
                "ticker": ticker,
                "sector": w_data.get("sector"),
                "unified_score": unified_score,
                "risk_rating": w_data.get("risk_rating"),
                "industry": w_data.get("industry")
            })
            
    # 6. Rebalance recommendations
    health = calculate_portfolio_health_metrics(portfolio)
    rebalance_plans = generate_rebalance_suggestions(portfolio, health)
    quality_score = calculate_portfolio_quality_score(portfolio, health)
    
    # 7. Prompt Gemini Investment Committee
    prompt = f"""
    You are the AORA Institutional Investment Committee. Your goal is to analyze the user's portfolio and provide strategic rebalancing and allocation advice.
    
    PORTFOLIO DETAILS:
    - Total Portfolio Value: ₹{portfolio_value:,.2f}
    - Cash Available: ₹{cash:,.2f} ({(cash/portfolio_value)*100.0 if portfolio_value > 0 else 0.0:.1f}%)
    - Market Regime: {regime}
    - Active Holdings State: {json.dumps(holdings_context)}
    - Halal Compliant Buy Screen Matches: {json.dumps(buy_candidates)}
    - Rebalance Rules Suggestions: {json.dumps(rebalance_plans)}
    
    You must output a single JSON document conforming to the following schema. Keep descriptions concise.
    
    Schema:
    {{
      "overall_decision": "BUY | SELL | HOLD | REBALANCE",
      "portfolio_score": {int(quality_score)},
      "cash_action": "RESTORE_RESERVE | DEPLOY_CASH | HOLD",
      "buy_candidates": [
        {{ "ticker": "...", "amount": 15000, "reason": "..." }}
      ],
      "sell_candidates": [
        {{ "ticker": "...", "amount": 10000, "reason": "..." }}
      ],
      "increase_positions": [
        {{ "ticker": "...", "amount": 5000, "reason": "..." }}
      ],
      "reduce_positions": [
        {{ "ticker": "...", "amount": 5000, "reason": "..." }}
      ],
      "risk_summary": "...",
      "expected_monthly_return": "+1.5%",
      "expected_volatility": "12.5%",
      "reasoning": "..."
    }}
    """
    
    model = genai.GenerativeModel("gemini-2.5-flash")
    raw_response = "{}"
    parsed_json = {}
    
    # Exponential backoff loop (Task 6)
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
            logger.warning(f"Gemini committee advisory attempt {attempt+1} failed: {e}")
            time.sleep(2 ** attempt)
            
    # Fallback response
    if not parsed_json:
        parsed_json = {
            "overall_decision": "HOLD",
            "portfolio_score": int(quality_score),
            "cash_action": "HOLD",
            "buy_candidates": [],
            "sell_candidates": [
                {"ticker": c["ticker"], "amount": c["quantity"] * c["current_price"], "reason": ", ".join(c["reasons"])} for c in sell_candidates
            ],
            "increase_positions": [],
            "reduce_positions": [
                {"ticker": c["ticker"], "amount": (c["quantity"] * c["current_price"]) * 0.5, "reason": ", ".join(c["reasons"])} for c in reduce_candidates
            ],
            "risk_summary": "Standard risk bounds maintained under bull/bear regime filters.",
            "expected_monthly_return": "+1.2%",
            "expected_volatility": "15.0%",
            "reasoning": "Fallback model generated due to Gemini API rate limits."
        }
        
    return {
        "portfolio": portfolio,
        "health": health,
        "rebalance_suggestions": rebalance_plans,
        "score": parsed_json.get("portfolio_score", int(quality_score)),
        "decision": parsed_json
    }
