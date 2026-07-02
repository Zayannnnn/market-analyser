import os
import json
import logging
import google.generativeai as genai
from datetime import datetime, timedelta
from typing import List, Dict, Any
from app.config import settings
from app.db import db

logger = logging.getLogger(__name__)

# Configure Gemini
genai.configure(api_key=settings.gemini_api_key)

def generate_stock_explanation(stock: Dict[str, Any], news_headlines: List[str]) -> Dict[str, Any]:
    """
    Calls Gemini Flash to write the detailed financial analysis and growth indicators.
    """
    ticker = stock["ticker"]
    company_name = stock.get("company_name", ticker)
    price = stock.get("current_price", 0.0)
    change = stock.get("daily_change", 0.0)
    score = stock.get("unified_score", 0)
    indicators = stock.get("technical_indicators", {})
    
    prompt = f"""
    You are a senior financial analyst writing a concise intelligence briefing for the stock '{company_name}' ({ticker}).
    
    Current Indicators:
    - Stock Price: ${price:.2f} ({"+" if change >= 0 else ""}{change:.2f}% daily change)
    - Valuation Score: {score}/100
    - Technical Metrics: RSI={indicators.get('rsi')}, MACD={indicators.get('macd')}, Volume Surge={indicators.get('volume_surge')}x, Breakout Detected={indicators.get('breakout_detected')}
    - Recent News Headlines: {news_headlines}
    
    Evaluate this stock's performance and output a JSON analysis containing:
    1. "why_ranked": A 2-sentence executive summary explaining why the stock scored highly in our technical/sentiment engine.
    2. "bullish_factors": A list of exactly 3 strong arguments or growth vectors in favor of the stock's short-term upward momentum.
    3. "risk_factors": A list of exactly 2 warning signs, potential headwinds, or technical resistance risks.
    4. "confidence_level": The confidence level of our rating, which must be exactly one of: "Low", "Medium", "High".
    
    Return ONLY the raw JSON object. Do not include markdown codeblocks or extra text.
    """
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        
        result = json.loads(response.text.strip())
        
        # Verify lists
        bullish = result.get("bullish_factors", ["Strong technical indicators", "Positive news coverage", "High trading momentum"])
        risks = result.get("risk_factors", ["Broader market volatility", "Potential technical overbought correction"])
        confidence = str(result.get("confidence_level", "Medium")).capitalize()
        if confidence not in ["Low", "Medium", "High"]:
            confidence = "Medium"
            
        return {
            "why_ranked": result.get("why_ranked", f"Ticker {ticker} ranked highly due to recent breakouts and positive news coverage."),
            "bullish_factors": bullish[:3],
            "risk_factors": risks[:2],
            "confidence_level": confidence
        }
    except Exception as e:
        logger.error(f"Gemini API explanation generation failed for {ticker}: {e}")
        # Default fallback
        return {
            "why_ranked": f"Ticker {ticker} shows strong momentum signals based on technical indicators and volume spikes.",
            "bullish_factors": ["High volume breakout", "Bullish MACD trend", "Positive news sentiment"],
            "risk_factors": ["Resistance at 52-week highs", "Macro sector headwinds"],
            "confidence_level": "Medium"
        }

def process_ai_explanations(top10_stocks: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Agent 5 Execution: Generates/reads detailed explanations for the Top 10 stocks.
    Implements a strict cache: if explanation in Firestore is < 2 hours old and score is similar,
    skips Gemini Flash call.
    Saves output to analysis.json.
    """
    logger.info("Agent 5: Explanation Agent starting cycle.")
    
    # 1. Load top 10 stocks if not provided
    if top10_stocks is None:
        input_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "top10.json")
        try:
            if os.path.exists(input_path):
                with open(input_path, "r") as f:
                    top10_stocks = json.load(f)
            else:
                top10_stocks = []
        except Exception as e:
            logger.error(f"Could not load top10.json: {e}")
            top10_stocks = []
            
    analysis_results = []
    
    # 2. Process explanations
    for stock in top10_stocks:
        ticker = stock["ticker"]
        current_score = stock["unified_score"]
        
        # Pull recent headlines from Firestore for prompt
        headlines = []
        try:
            news_docs = db.collection("news").where("ticker", "==", ticker).limit(3).get()
            headlines = [doc.to_dict().get("title", "") for doc in news_docs]
        except Exception as e:
            logger.warning(f"Failed to query news headlines for explanation prompt: {e}")
            
        # Cache Check: Query Firestore 'ai_analysis' collection
        cached_doc = None
        try:
            cached_doc = db.collection("ai_analysis").document(ticker).get()
        except Exception as e:
            logger.warning(f"Error querying ai_analysis cache for {ticker}: {e}")
            
        explanation = None
        cache_hit = False
        
        if cached_doc and cached_doc.exists:
            cached_data = cached_doc.to_dict()
            analyzed_at_str = cached_data.get("analyzed_at", "")
            cached_score = cached_data.get("unified_score", 0)
            
            if analyzed_at_str:
                try:
                    analyzed_at = datetime.fromisoformat(analyzed_at_str.replace("Z", ""))
                    age = datetime.utcnow() - analyzed_at
                    
                    # Cache rule: less than 2 hours old and score difference within 3 points
                    if age < timedelta(hours=2) and abs(cached_score - current_score) <= 3:
                        explanation = {
                            "why_ranked": cached_data["why_ranked"],
                            "bullish_factors": cached_data["bullish_factors"],
                            "risk_factors": cached_data["risk_factors"],
                            "confidence_level": cached_data["confidence_level"]
                        }
                        cache_hit = True
                        logger.debug(f"Cache HIT for AI explanation of stock {ticker}")
                except Exception as e:
                    logger.error(f"Error parsing analyzed_at timestamp: {e}")
                    
        if not cache_hit:
            logger.info(f"Cache MISS. Calling Gemini Flash to generate explanation for {ticker}")
            explanation = generate_stock_explanation(stock, headlines)
            
            # Store/Update in Firestore
            try:
                ai_doc = explanation.copy()
                ai_doc["unified_score"] = current_score
                ai_doc["analyzed_at"] = datetime.utcnow().isoformat() + "Z"
                db.collection("ai_analysis").document(ticker).set(ai_doc)
            except Exception as e:
                logger.error(f"Failed storing AI analysis to Firestore: {e}")
                
        # Append explanation to stock dictionary in memory for API response
        stock_analyzed = stock.copy()
        stock_analyzed["ai_explanation"] = explanation
        analysis_results.append(stock_analyzed)
        
    # Write output to analysis.json locally
    output_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "analysis.json")
    try:
        with open(output_path, "w") as f:
            json.dump(analysis_results, f, indent=2)
        logger.info(f"Agent 5: Explanation Agent finished. Saved AI analysis to {output_path}.")
    except Exception as e:
        logger.error(f"Failed writing analysis.json: {e}")
        
    return analysis_results
