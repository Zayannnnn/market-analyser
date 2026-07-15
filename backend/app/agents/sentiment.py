import os
import json
import logging
import time
import google.generativeai as genai
from typing import List, Dict, Any
from app.config import settings
from app.db import db
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

logger = logging.getLogger(__name__)

# Configure Gemini
genai.configure(api_key=settings.gemini_api_key)

def analyze_article_sentiment(ticker: str, title: str, summary: str) -> Dict[str, Any]:
    """
    Calls Gemini Flash to analyze the sentiment and impact of a single article.
    """
    prompt = f"""
    Analyze the following news article for its potential impact on the stock ticker '{ticker}'.
    
    Article Title: {title}
    Article Summary: {summary}
    
    You must evaluate the sentiment and expected short-term price impact of this news on the company.
    
    Provide your response in raw JSON format with the following fields:
    - "sentiment_score": An integer between -100 (extremely bearish/negative) and +100 (extremely bullish/positive). Use 0 for purely neutral news.
    - "impact_level": The strength of the news impact on the stock price. Must be exactly one of: "low", "medium", "high".
    
    Return ONLY the raw JSON object. Do not include markdown codeblocks or extra text.
    """
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        
        repaired = repair_json_text(response.text.strip())
        result = json.loads(repaired)
        score = int(result.get("sentiment_score", 0))
        impact = str(result.get("impact_level", "low")).lower()
        
        if impact not in ["low", "medium", "high"]:
            impact = "low"
            
        return {
            "sentiment_score": max(-100, min(100, score)),
            "impact_level": impact
        }
    except Exception as e:
        logger.error(f"Gemini API sentiment analysis call failed for {ticker}: {e}")
        return {
            "sentiment_score": 0.0,
            "impact_level": "low"
        }

def analyze_stock_news_sentiment(ticker: str, articles: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Agent 2.5: Summarizes all recent news articles for a stock
    and outputs a structured JSON analysis (summary, sentiment, impact_score, key_events, risks, opportunities).
    """
    if not articles:
        return get_fallback_news_analysis(ticker)
        
    news_context = ""
    # Use top 6 relevant articles
    for idx, art in enumerate(articles[:6]):
        news_context += f"Article #{idx+1}:\nTitle: {art.get('title')}\nSource: {art.get('source')}\nSummary: {art.get('summary')}\n\n"
        
    prompt = f"""
    You are an AI investment intelligence news analyst.
    Analyze all recent news articles for the stock '{ticker}'.
    
    News Articles Context:
    {news_context}
    
    Summarize the news and output a STRICT JSON response exactly matching this format:
    {{
      "summary": "A 2-3 sentence clear and concise summary of the overall news sentiment and current developments.",
      "sentiment": "Bullish", // Must be exactly one of: Bullish, Bearish, Neutral
      "impact_score": 75,     // An integer between 0 (very negative) and 100 (very positive), where 50 is neutral
      "key_events": [
         "Event or development 1",
         "Event or development 2"
      ],
      "risks": [
         "Risk factor or headwind identified from the news"
      ],
      "opportunities": [
         "Growth opportunities or catalysts identified from the news"
      ]
    }}
    
    Output ONLY the raw JSON object. Do not include any markdown blocks, comments, or extra text.
    """
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            model = genai.GenerativeModel("gemini-2.5-flash")
            response = model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            
            repaired = repair_json_text(response.text.strip())
            result = json.loads(repaired)
            
            summary = str(result.get("summary", ""))
            sentiment = str(result.get("sentiment", "Neutral")).capitalize()
            if sentiment not in ["Bullish", "Bearish", "Neutral"]:
                sentiment = "Neutral"
                
            try:
                impact_score = int(result.get("impact_score", 50))
            except (ValueError, TypeError):
                impact_score = 50
                
            key_events = result.get("key_events", [])
            risks = result.get("risks", [])
            opportunities = result.get("opportunities", [])
            
            analysis = {
                "summary": summary,
                "sentiment": sentiment,
                "impact_score": max(0, min(100, impact_score)),
                "key_events": key_events if isinstance(key_events, list) else [],
                "risks": risks if isinstance(risks, list) else [],
                "opportunities": opportunities if isinstance(opportunities, list) else [],
                "analyzed_at": time.time()
            }
            
            # Store in Firestore under news_analysis collection
            try:
                db.collection("news_analysis").document(ticker).set(analysis)
            except Exception as fe:
                logger.error(f"Failed to save news analysis in Firestore for {ticker}: {fe}")
                
            return analysis
            
        except Exception as e:
            logger.warning(f"Error parsing Gemini news analysis on attempt {attempt + 1}: {e}")
            if attempt == max_retries - 1:
                logger.error(f"Gemini news analysis retries exhausted for {ticker}: {e}")
            else:
                time.sleep(1.0)
                
    return get_fallback_news_analysis(ticker)

def get_fallback_news_analysis(ticker: str) -> Dict[str, Any]:
    """Returns default news analysis structure on failure or missing articles."""
    return {
        "summary": f"No recent corporate news or breaking headlines registered for {ticker}.",
        "sentiment": "Neutral",
        "impact_score": 50,
        "key_events": ["No recent news updates are currently available."],
        "risks": ["Standard market macroeconomic sector changes."],
        "opportunities": ["Ongoing corporate growth operations."],
        "analyzed_at": time.time()
    }

def process_sentiment_analysis(matched_news: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Agent 2 Execution: Runs sentiment checks on all news articles.
    Implements a strict cache: if the article has been analyzed in Firestore, skips Gemini call.
    Saves output to sentiment.json.
    """
    logger.info("Agent 2: Sentiment Agent starting cycle.")
    
    if matched_news is None:
        input_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "clean_news.json")
        try:
            if os.path.exists(input_path):
                with open(input_path, "r") as f:
                    matched_news = json.load(f)
            else:
                matched_news = []
        except Exception as e:
            logger.error(f"Could not load clean_news.json: {e}")
            matched_news = []
            
    processed_news = []
    
    for item in matched_news:
        doc_id = item["id"]
        ticker = item["ticker"]
        
        cached_doc = None
        try:
            cached_doc = db.collection("news").document(doc_id).get()
        except Exception as e:
            logger.warning(f"Error querying Firestore cache for news {doc_id}: {e}")
            
        sentiment_score = 0.0
        impact_level = "low"
        cache_hit = False
        
        if cached_doc and cached_doc.exists:
            cached_data = cached_doc.to_dict()
            if "sentiment_score" in cached_data and cached_data.get("sentiment_score") is not None and cached_data.get("sentiment_score") != 0.0:
                sentiment_score = cached_data["sentiment_score"]
                impact_level = cached_data.get("impact_level", "low")
                cache_hit = True
                logger.debug(f"Cache HIT for news item {doc_id} ({ticker})")
                
        if not cache_hit:
            logger.info(f"Cache MISS. Invocating Gemini Flash for news item {doc_id} ({ticker})")
            sentiment_data = analyze_article_sentiment(
                ticker=ticker,
                title=item["title"],
                summary=item["summary"]
            )
            sentiment_score = sentiment_data["sentiment_score"]
            impact_level = sentiment_data["impact_level"]
            
        updated_item = item.copy()
        updated_item["sentiment_score"] = float(sentiment_score)
        updated_item["impact_level"] = impact_level
        processed_news.append(updated_item)
        
        try:
            db.collection("news").document(doc_id).set(updated_item, merge=True)
        except Exception as e:
            logger.error(f"Failed to update news sentiment in Firestore: {e}")
            
    output_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "sentiment.json")
    try:
        with open(output_path, "w") as f:
            json.dump(processed_news, f, indent=2)
        logger.info(f"Agent 2: Sentiment Agent finished. Saved {len(processed_news)} articles to {output_path}.")
    except Exception as e:
        logger.error(f"Failed writing sentiment.json: {e}")
        
    return processed_news
