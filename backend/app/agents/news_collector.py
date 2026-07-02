import os
import json
import logging
import hashlib
from typing import List, Dict, Any
from app.db import db
from app.data_sources.rss_scrapers import fetch_rss_articles
from app.ticker_registry import get_stock_master

logger = logging.getLogger(__name__)

def load_ticker_map() -> Dict[str, List[str]]:
    """
    Builds ticker keywords from canonical StockMaster. This avoids stale Firestore
    company names and prevents news from being mapped to non-canonical aliases.
    """
    ticker_map = {}
    for entry in get_stock_master():
        ticker = entry["ticker"]
        name = entry["companyName"]
        keywords = [ticker, name]
        name_clean = (
            name.replace("Limited", "")
            .replace("Ltd.", "")
            .replace("Ltd", "")
            .replace("Corp.", "")
            .replace("Corporation", "")
            .strip()
        )
        if name_clean and name_clean not in keywords:
            keywords.append(name_clean)
        for term in entry.get("searchTerms", []):
            if term not in keywords:
                keywords.append(term)
        ticker_map[ticker] = keywords
    return ticker_map

def collect_and_match_news() -> List[Dict[str, Any]]:
    """
    Agent 1 Execution: Scrapes news, deduplicates, maps to NSE tickers,
    saves output to clean_news.json and writes items to Firestore.
    """
    logger.info("Agent 1: News Collector starting cycle.")
    
    # 1. Fetch raw news feeds
    raw_articles = fetch_rss_articles()
    
    # 2. Load Ticker mapping keywords
    ticker_map = load_ticker_map()
    
    matched_news = []
    seen_urls = set()
    
    # 3. Match tickers in titles/summaries
    for article in raw_articles:
        url = article["url"]
        if url in seen_urls:
            continue
            
        title = article["title"].lower()
        summary = article["summary"].lower()
        
        matched_tickers = []
        for ticker, keywords in ticker_map.items():
            for kw in keywords:
                pattern = r'\b' + re.escape(kw.lower()) + r'\b'
                if re.search(pattern, title) or re.search(pattern, summary):
                    matched_tickers.append(ticker)
                    break  # Found match for this ticker, skip other keywords
                    
        # Add to collection if matched
        for ticker in matched_tickers:
            # Generate unique identifier hash of url + ticker
            doc_id = hashlib.md5(f"{url}_{ticker}".encode()).hexdigest()
            
            clean_item = {
                "id": doc_id,
                "ticker": ticker,
                "title": article["title"],
                "url": url,
                "source": article["source"],
                "summary": article["summary"],
                "published_at": article["published_at"]
            }
            matched_news.append(clean_item)
            seen_urls.add(url)
            
            # Write to Firestore 'news' collection
            try:
                db.collection("news").document(doc_id).set(clean_item, merge=True)
            except Exception as e:
                logger.error(f"Failed to store news article in Firestore: {e}")

    # Write output to clean_news.json locally in the backend directory
    output_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "clean_news.json")
    try:
        with open(output_path, "w") as f:
            json.dump(matched_news, f, indent=2)
        logger.info(f"Agent 1: News Collector finished. Saved {len(matched_news)} matched articles to {output_path}.")
    except Exception as e:
        logger.error(f"Failed writing clean_news.json: {e}")
        
    return matched_news

# Make re module available inside file for regex search
import re
