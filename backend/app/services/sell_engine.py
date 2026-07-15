import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

def evaluate_sell_decision(
    ticker: str,
    current_price: float,
    entry_price: float,
    stop_loss: float,
    target: float,
    indicators: Dict[str, Any],
    news_sentiment_score: float, # -1.0 to +1.0
    market_regime: str,          # "Strong Bull" | "Bull" | "Neutral" | "Bear" | "Strong Bear"
    upcoming_event_detected: bool,
    risk_score: float            # 10 to 100
) -> Dict[str, Any]:
    """
    Institutional Sell Engine (Phase 6.2).
    Evaluates indicators, news, event risk, regime trends, and risk thresholds to return SELL, REDUCE, or HOLD.
    """
    reasons = []
    score = 0 # Cumulative bearish count
    
    # 1. Stop Loss & Target Checks
    if current_price <= stop_loss:
        reasons.append("Trailing Stop Loss breached.")
        return {"decision": "SELL", "reasons": reasons, "severity": "CRITICAL"}
        
    if current_price >= target:
        reasons.append("Take-profit target achieved.")
        return {"decision": "SELL", "reasons": reasons, "severity": "HIGH"}
        
    # 2. Technical breakdowns
    ema20 = float(indicators.get("ema20", current_price))
    ema50 = float(indicators.get("ema50", current_price))
    rsi = float(indicators.get("rsi", 50.0))
    macd_desc = indicators.get("macd_desc", "Neutral")
    
    if current_price < ema50:
        score += 2
        reasons.append("Price closed below EMA50 trend support.")
    elif current_price < ema20:
        score += 1
        reasons.append("Price closed below short-term EMA20 support.")
        
    if rsi < 35:
        score += 2
        reasons.append("RSI shows extreme bearish momentum (RSI < 35).")
        
    if "Bearish" in macd_desc:
        score += 1
        reasons.append("MACD Bearish crossover active.")
        
    # 3. Sentiment & Event Risks
    if news_sentiment_score < -0.25:
        score += 2
        reasons.append(f"Negative news sentiment detected (score: {news_sentiment_score}).")
        
    if upcoming_event_detected:
        score += 1
        reasons.append("Upcoming corporate action or results release date filter triggered.")
        
    # 4. Market Regime weaknesses
    if market_regime == "Strong Bear":
        score += 3
        reasons.append("Broad market is in a Strong Bear regime.")
    elif market_regime == "Bear":
        score += 1.5
        reasons.append("Broad market is in a Bear regime.")
        
    # 5. Risk score threshold
    if risk_score > 75:
        score += 2
        reasons.append(f"Asset risk rating elevated above institutional limits ({risk_score}/100).")
        
    # Decision compilation
    if score >= 6:
        decision = "SELL"
    elif score >= 3:
        decision = "REDUCE"
    else:
        decision = "HOLD"
        
    return {
        "decision": decision,
        "reasons": reasons,
        "severity": "HIGH" if score >= 6 else "MEDIUM" if score >= 3 else "LOW",
        "sell_score": score
    }
