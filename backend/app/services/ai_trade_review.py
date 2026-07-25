import json
import logging
import time
import pandas as pd
import google.generativeai as genai
from typing import Dict, Any, List, Optional
from app.config import settings
from app.db import db
from app.data_sources.market_data import get_market_data
from app.services.technical_indicators import compute_local_indicators
from app.agents.explanation import get_live_portfolio_data
from app.services.risk_engine import calculate_portfolio_risk

logger = logging.getLogger(__name__)

# Configure Gemini Generative AI
genai.configure(api_key=settings.gemini_api_key)

def repair_json_text(text: str) -> str:
    """Strips leading/trailing markdown code blocks and whitespace."""
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()

def get_recent_news_sentiment(ticker: str) -> Dict[str, Any]:
    """Retrieves recent news articles for a ticker from Firestore and calculates average sentiment."""
    try:
        # Query Firestore "news" collection for ticker
        docs = db.collection("news").where("ticker", "==", ticker.upper()).limit(10).get()
        articles = [doc.to_dict() for doc in docs]
        if not articles:
            return {"sentiment_score": 0.0, "article_count": 0, "headlines": []}
        
        scores = [float(a.get("sentiment_score", 0.0)) for a in articles]
        headlines = [a.get("title", "") for a in articles if a.get("title")]
        avg_score = sum(scores) / len(scores) if scores else 0.0
        return {
            "sentiment_score": round(avg_score, 2),
            "article_count": len(articles),
            "headlines": headlines[:5]
        }
    except Exception as e:
        logger.warning(f"Error fetching news sentiment for {ticker}: {e}")
        return {"sentiment_score": 0.0, "article_count": 0, "headlines": []}

def calculate_historical_volatility(closes: List[float]) -> float:
    """Calculates annualized historical volatility percentage from daily close prices."""
    if len(closes) < 5:
        return 20.0  # Default baseline volatility
    try:
        s = pd.Series(closes)
        returns = s.pct_change().dropna()
        daily_std = returns.std()
        annual_vol = daily_std * (252 ** 0.5) * 100.0
        return round(float(annual_vol), 2)
    except Exception as e:
        logger.warning(f"Error calculating volatility: {e}")
        return 20.0

async def generate_ai_trade_review(
    ticker: str,
    quantity: int,
    side: str,
    price: Optional[float] = None,
    order_type: str = "MARKET"
) -> Dict[str, Any]:
    """
    Independent AI Trade Review Engine.
    Collects real market, technical, news, and portfolio metrics, feeds them to Gemini,
    and returns a structured decision evaluation before execution.
    """
    logger.info(f"Generating AI Trade Review for {side} {quantity} {ticker} ({order_type})")
    
    # 1. Fetch Market Data & Local Technical Indicators
    try:
        market_data = get_market_data(ticker)
        current_price = price if price is not None and price > 0 else market_data.get("price", 0.0)
        
        closes = market_data.get("history_close", [])
        highs = market_data.get("history_high", [])
        lows = market_data.get("history_low", [])
        volumes = market_data.get("history_volume", [])
        
        technicals = compute_local_indicators(closes, highs, lows, volumes)
        volatility = calculate_historical_volatility(closes)
    except Exception as e:
        logger.error(f"Error gathering market & technical data for review of {ticker}: {e}")
        raise ValueError(f"Could not load market data or technicals for ticker: {ticker}")

    # 2. News Sentiment
    news_sentiment = get_recent_news_sentiment(ticker)
    
    # 3. Fetch Portfolio Data
    portfolio = get_live_portfolio_data()
    
    # 4. Risk Engine calculations
    try:
        risk_data = calculate_portfolio_risk(
            portfolio=portfolio,
            target_ticker=ticker,
            target_price=current_price,
            target_atr=technicals.get("atr", 1.0),
            target_support=technicals.get("support", current_price * 0.95)
        )
    except Exception as e:
        logger.error(f"Error calculating risk guidelines for {ticker}: {e}")
        risk_data = {
            "portfolio_value": 100000.0,
            "cash_available": 100000.0,
            "cash_exposure_pct": 100.0,
            "sector_exposure": {},
            "position_exposure_pct": 0.0,
            "suggested_qty": quantity,
            "risk_score": 50,
            "expected_portfolio_impact": "N/A"
        }

    # 5. Build Gemini Prompt
    prompt = f"""
You are the Lead Investment Strategist at AORA AI Stock Intelligence.
Analyze the proposed trade parameters and unified quantitative indicators to generate a structured AI Trade Review.

PROPOSED TRADE:
- Ticker: {ticker}
- Side: {side.upper()}
- Proposed Quantity: {quantity}
- Proposed Price (if Limit): {price if price else 'Market Price (~' + str(current_price) + ')'}
- Order Type: {order_type}

MARKET & TECHNICAL INDICATORS:
- Current Price: ₹{current_price}
- Annualized Volatility: {volatility}%
- RSI (14): {technicals.get('rsi')}
- MACD Description: {technicals.get('macd_desc')}
- 50-day SMA: ₹{technicals.get('sma50')}
- 200-day SMA: ₹{technicals.get('sma200')}
- ATR (14): ₹{technicals.get('atr')}
- Support Level: ₹{technicals.get('support')}
- Resistance Level: ₹{technicals.get('resistance')}
- Breakout Detected: {technicals.get('breakout_detected')}

NEWS SENTIMENT:
- Average Sentiment Score (-100 to +100): {news_sentiment.get('sentiment_score')}
- Recent Headlines: {json.dumps(news_sentiment.get('headlines'))}

PORTFOLIO & RISK METRICS:
- Total Portfolio Value: ₹{risk_data.get('portfolio_value')}
- Cash Available: ₹{risk_data.get('cash_available')}
- Cash Exposure: {risk_data.get('cash_exposure_pct')}%
- Current Position Exposure for {ticker}: {risk_data.get('position_exposure_pct')}%
- Sector Exposure for this sector: {json.dumps(risk_data.get('sector_exposure'))}
- Portfolio Risk Score (10-100): {risk_data.get('risk_score')}
- Suggested Position Sizing (ATR-based): {risk_data.get('suggested_qty')} shares
- Expected Portfolio Impact: {risk_data.get('expected_portfolio_impact')}

INSTRUCTIONS:
Generate a synthesized review of the trade.
Format the response strictly as a JSON object with these exact keys:
{{
  "confidence": int,           // Score from 0 to 100 representing conviction in the recommendation
  "recommendation": string,    // Must be "BUY", "SELL", or "HOLD"
  "risk": string,              // Must be "Low", "Medium", or "High"
  "expected_reward": string,   // Description of target gains or potential target price
  "suggested_quantity": int,   // Recommended shares count based on cash and ATR risk limits
  "reasons": [string],         // 3-4 bullet points justifying the decision (technicals, news, portfolio alignment)
  "warnings": [string]         // 1-2 warnings about risk, concentration, market volatility, or ATR stop losses
}}
Do not write any text other than the JSON object.
"""

    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        
        raw_text = response.text.strip()
        repaired_text = repair_json_text(raw_text)
        result = json.loads(repaired_text)
        
        # Verify schema defaults
        if "confidence" not in result:
            result["confidence"] = 70
        if "recommendation" not in result:
            result["recommendation"] = "HOLD"
        if "risk" not in result:
            result["risk"] = "Medium"
        if "reasons" not in result or not isinstance(result["reasons"], list):
            result["reasons"] = ["Analysis completed successfully."]
        if "warnings" not in result or not isinstance(result["warnings"], list):
            result["warnings"] = []
        if "suggested_quantity" not in result:
            result["suggested_quantity"] = risk_data.get("suggested_qty", quantity)
        if "expected_reward" not in result:
            result["expected_reward"] = f"Upside target based on technical resistance of ₹{technicals.get('resistance')}"

        return result

    except Exception as e:
        logger.error(f"Gemini failed to generate AI trade review for {ticker}: {e}", exc_info=True)
        # Fallback heuristic review generator
        recommendation = "HOLD"
        rsi = technicals.get("rsi", 50.0)
        macd = technicals.get("macd_desc", "Neutral")
        
        if side.upper() == "BUY":
            if rsi < 40 or "Bullish" in macd:
                recommendation = "BUY"
        elif side.upper() == "SELL":
            if rsi > 70 or "Bearish" in macd:
                recommendation = "SELL"
                
        return {
            "confidence": 60,
            "recommendation": recommendation,
            "risk": "Medium" if volatility < 30 else "High",
            "expected_reward": f"Target resistance level ₹{technicals.get('resistance')}",
            "suggested_quantity": risk_data.get("suggested_qty", quantity),
            "reasons": [
                f"RSI is currently at {rsi} (Neutral range).",
                f"MACD indicator indicates a {macd}.",
                f"Annualized historical volatility of the asset is {volatility}%."
            ],
            "warnings": [
                "Gemini review generation timed out or failed. Reverting to local heuristic indicators rules."
            ]
        }
