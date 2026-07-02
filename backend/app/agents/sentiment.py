import os
import json
import logging
import google.generativeai as genai
from typing import List, Dict, Any
from app.config import settings
from app.db import db

logger = logging.getLogger(__name__)

# Configure Gemini
genai.configure(api_key=settings.gemini_api_key)

def analyze_article_sentiment(ticker: str, title: str, summary: str) -> Dict[str, Any]:
    """
    Calls Gemini Flash to analyze the sentiment and impact of an article.
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
        
        result = json.loads(response.text.strip())
        score = int(result.get("sentiment_score", 0))
        impact = str(result.get("impact_level", "low")).lower()
        
        # Validate impact level
        if impact not in ["low", "medium", "high"]:
            impact = "low"
            
        return {
            "sentiment_score": max(-100, min(100, score)),
            "impact_level": impact
        }
    except Exception as e:
        logger.error(f"Gemini API sentiment analysis call failed for {ticker}: {e}")
        # Default fallback
        return {
            "sentiment_score": 0.0,
            "impact_level": "low"
        }

def process_sentiment_analysis(matched_news: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Agent 2 Execution: Runs sentiment checks on all news articles.
    Implements a strict cache: if the article has been analyzed in Firestore, skips Gemini call.
    Saves output to sentiment.json.
    """
    logger.info("Agent 2: Sentiment Agent starting cycle.")
    
    # 1. Load clean news if list is not provided
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
    
    # 2. Iterate news and evaluate sentiment
    for item in matched_news:
        doc_id = item["id"]
        ticker = item["ticker"]
        
        # Cache Check: Query Firestore first
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
            # If sentiment is already computed and stored, use it
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
            
        # Update item
        updated_item = item.copy()
        updated_item["sentiment_score"] = float(sentiment_score)
        updated_item["impact_level"] = impact_level
        processed_news.append(updated_item)
        
        # Store back in Firestore
        try:
            db.collection("news").document(doc_id).set(updated_item, merge=True)
        except Exception as e:
            logger.error(f"Failed to update news sentiment in Firestore: {e}")
            
    # Write output to sentiment.json locally
    output_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "sentiment.json")
    try:
        with open(output_path, "w") as f:
            json.dump(processed_news, f, indent=2)
        logger.info(f"Agent 2: Sentiment Agent finished. Saved {len(processed_news)} articles to {output_path}.")
    except Exception as e:
        logger.error(f"Failed writing sentiment.json: {e}")
        
    return processed_news
