import json
import logging
import time
import pandas as pd
import google.generativeai as genai
from typing import Dict, Any, List
from app.config import settings
from app.db import db
from app.data_sources.market_data import get_market_data
from app.services.technical_indicators import compute_local_indicators
from app.agents.explanation import get_live_portfolio_data, repair_json_text
from app.services.market_regime import determine_market_regime
from app.services.ai_trade_review import get_recent_news_sentiment, calculate_historical_volatility

logger = logging.getLogger(__name__)

# Configure Gemini Generative AI
genai.configure(api_key=settings.gemini_api_key)

async def generate_holdings_analysis() -> Dict[str, Any]:
    """
    Scans every active position in the live portfolio, fetches indicators, news, 
    and portfolio exposure context, and runs Gemini to output recommendations:
    BUY, HOLD, SELL, REDUCE, ACCUMULATE.
    """
    logger.info("Running E2E Portfolio Holdings AI Analysis Engine...")
    
    # 1. Fetch live portfolio details
    portfolio = get_live_portfolio_data()
    if not portfolio.get("authenticated", False):
        return {
            "status": "error",
            "message": "Broker authentication required.",
            "holdings": []
        }
        
    holdings = portfolio.get("holdings", [])
    cash = float(portfolio.get("cash_available", 0.0))
    
    if not holdings:
        return {
            "status": "success",
            "message": "No active holdings found in portfolio.",
            "holdings": []
        }
        
    # Resolve total portfolio value
    holdings_value = 0.0
    for h in holdings:
        qty = float(h.get("quantity", h.get("qty", 0.0)))
        price = float(h.get("last_price", h.get("current_price", 0.0)))
        holdings_value += qty * price
    total_val = cash + holdings_value
    
    # 2. Get Broad regime
    regime_data = determine_market_regime()
    regime = regime_data.get("regime", "Neutral")
    
    analysis_results = []
    
    for h in holdings:
        ticker = h.get("ticker", h.get("tradingsymbol", "Unknown")).upper()
        qty = float(h.get("quantity", h.get("qty", 0.0)))
        avg_cost = float(h.get("average_price", 0.0))
        current_price = float(h.get("last_price", h.get("current_price", 0.0)))
        sector = h.get("sector", "Other") or "Other"
        
        allocation_pct = round(((qty * current_price) / total_val) * 100, 2) if total_val > 0 else 0.0
        
        # Gather tech indicators
        try:
            market_data = get_market_data(ticker)
            closes = market_data.get("history_close", [])
            highs = market_data.get("history_high", [])
            lows = market_data.get("history_low", [])
            volumes = market_data.get("history_volume", [])
            
            technicals = compute_local_indicators(closes, highs, lows, volumes)
            volatility = calculate_historical_volatility(closes)
        except Exception as e:
            logger.warning(f"Failed to fetch market details for holding {ticker}: {e}")
            technicals = {}
            volatility = 20.0
            
        # Get sentiment
        sentiment_data = get_recent_news_sentiment(ticker)
        
        # Build prompt for holding analysis
        prompt = f"""
        You are the Head Portfolio Manager at AORA AI Stock Intelligence.
        Analyze this active portfolio holding position and determine the optimal portfolio action.
        
        HOLDING DETAIL:
        - Ticker: {ticker}
        - Shares Held: {qty}
        - Average Purchase Price: ₹{avg_cost}
        - Current Market Price: ₹{current_price}
        - Current Allocation % of Portfolio: {allocation_pct}%
        - Sector: {sector}
        
        TECHNICAL INDICATORS:
        - RSI (14): {technicals.get('rsi', 'N/A')}
        - MACD Overlay: {technicals.get('macd_desc', 'N/A')}
        - Annualized Volatility: {volatility}%
        - Support Level: ₹{technicals.get('support', 'N/A')}
        - Resistance Level: ₹{technicals.get('resistance', 'N/A')}
        - 50-day SMA: ₹{technicals.get('sma50', 'N/A')}
        - 200-day SMA: ₹{technicals.get('sma200', 'N/A')}
        - ATR (14): ₹{technicals.get('atr', 'N/A')}
        
        NEWS SENTIMENT:
        - News Sentiment Score (-100 to +100): {sentiment_data.get('sentiment_score', 0.0)}
        - Recent Headlines: {json.dumps(sentiment_data.get('headlines', []))}
        
        PORTFOLIO CONTEXT:
        - Portfolio Regime: {regime}
        
        INSTRUCTIONS:
        Determine whether we should BUY more, HOLD, SELL out, REDUCE exposure, or ACCUMULATE on drops.
        You must return a single JSON document matching this exact schema:
        {{
          "decision": "string",          // Must be "BUY", "HOLD", "SELL", "REDUCE", or "ACCUMULATE"
          "confidence": int,             //Conviction score from 10 to 100
          "risk_score": int,             //Risk rating from 10 to 100
          "expected_reward": "string",   //Expected upside or target resistance description
          "reasoning": ["string"],       //3 concise points justifying the decision
          "suggested_quantity": int      //Number of shares to execute (e.g. trim amount, buy top-up, or full qty)
        }}
        Do not write any text outside of the JSON object.
        """
        
        result = None
        # Call Gemini with retries
        for attempt in range(3):
            try:
                model = genai.GenerativeModel("gemini-2.5-flash")
                response = model.generate_content(
                    prompt,
                    generation_config={"response_mime_type": "application/json"}
                )
                clean_txt = repair_json_text(response.text.strip())
                result = json.loads(clean_txt)
                if result:
                    break
            except Exception as e:
                logger.warning(f"Gemini holdings review attempt {attempt+1} failed for {ticker}: {e}")
                time.sleep(1.0)
                
        # Fallback heuristic
        if not result:
            rsi_val = float(technicals.get("rsi", 50.0))
            macd_desc = technicals.get("macd_desc", "Neutral")
            
            decision = "HOLD"
            reasons = ["Technical indicators are in neutral bounds.", "Regime checks show stable trends."]
            if rsi_val > 70:
                decision = "REDUCE"
                reasons = ["Asset is in overbought territory (RSI > 70). Recommend locking in partial gains."]
            elif rsi_val < 35:
                decision = "ACCUMULATE"
                reasons = ["Asset is in oversold territory (RSI < 35). High value setup for dollar cost averaging."]
            elif "Bearish" in macd_desc:
                decision = "HOLD"
                reasons = ["MACD indicates bearish momentum. Avoid new buying allocations for now."]
                
            result = {
                "decision": decision,
                "confidence": 60,
                "risk_score": 50 if volatility < 25 else 75,
                "expected_reward": f"Target resistance level ₹{technicals.get('resistance', current_price * 1.1):,.2f}",
                "reasoning": reasons,
                "suggested_quantity": int(qty * 0.2) if decision in ["REDUCE", "ACCUMULATE"] else int(qty)
            }
            
        analysis_results.append({
            "ticker": ticker,
            "shares_held": qty,
            "average_cost": avg_cost,
            "current_price": current_price,
            "allocation_pct": allocation_pct,
            "sector": sector,
            "analysis": result
        })
        
    # 3. Save findings to Firestore under holdings_analysis/current_holdings
    report_doc = {
        "status": "success",
        "updated_at": datetime_now_iso(),
        "holdings": analysis_results
    }
    try:
        db.collection("holdings_analysis").document("current_holdings").set(report_doc)
    except Exception as e:
        logger.error(f"Failed to cache holdings analysis in Firestore: {e}")
        
    return report_doc

def datetime_now_iso() -> str:
    from datetime import datetime
    return datetime.utcnow().isoformat() + "Z"
