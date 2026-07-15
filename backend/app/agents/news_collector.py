import os
import json
import logging
import hashlib
import re
import feedparser
import time
from typing import List, Dict, Any
from datetime import datetime, timedelta
from app.db import db
from app.ticker_registry import get_stock_master
from app.data_sources.rss_scrapers import clean_html, parse_rss_date

logger = logging.getLogger(__name__)

def load_ticker_map() -> Dict[str, List[str]]:
    """Builds ticker keyword lists fromcanonical registry."""
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

import urllib.parse

def fetch_targeted_news_for_stock(ticker: str, keywords: List[str]) -> List[Dict[str, Any]]:
    """Fetches targeted RSS feed articles for a specific stock ticker using search terms."""
    articles = []
    # Build query combining company name or ticker
    query_term = f'"{ticker}" OR "{keywords[1] if len(keywords) > 1 else ticker}" stock India'
    encoded_query = urllib.parse.quote_plus(query_term)
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-IN&gl=IN&ceid=IN:en"
    
    try:
        feed = feedparser.parse(url)
        if feed.entries:
            for entry in feed.entries[:8]:  # Top 8 targeted search entries
                title = entry.get("title", "")
                link = entry.get("link", "")
                summary = clean_html(entry.get("summary", "") or entry.get("description", ""))
                
                published = entry.get("published", "")
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    published = datetime(*entry.published_parsed[:6]).isoformat() + "Z"
                else:
                    published = parse_rss_date(published)
                    
                source = "Google News Search"
                if " - " in title:
                    parts = title.split(" - ")
                    title = " - ".join(parts[:-1])
                    source = parts[-1].strip()
                    
                articles.append({
                    "title": title.strip(),
                    "url": link,
                    "summary": summary[:400] + "..." if len(summary) > 400 else summary,
                    "source": source,
                    "published_at": published
                })
    except Exception as e:
        logger.warning(f"Error fetching targeted search news for {ticker}: {e}")
    return articles

def calculate_relevance_rank(title: str, summary: str, keywords: List[str], published_at: str) -> float:
    """Calculates a numerical score representing how relevant the article is to the keywords."""
    score = 0.0
    title_lower = title.lower()
    summary_lower = summary.lower()
    
    # Keyword matches
    for idx, kw in enumerate(keywords):
        kw_lower = kw.lower()
        pattern = r'\b' + re.escape(kw_lower) + r'\b'
        # Ticker or company name match has highest weight
        weight = 3.0 if idx == 0 else 1.5
        if re.search(pattern, title_lower):
            score += weight * 2.0
        if re.search(pattern, summary_lower):
            score += weight
            
    # Recency weight (boost if published within last 2 days)
    try:
        pub_time = datetime.fromisoformat(published_at.replace("Z", ""))
        age = datetime.utcnow() - pub_time
        if age.days <= 2:
            score += 2.0
        elif age.days <= 7:
            score += 1.0
    except Exception:
        pass
        
    return score

def collect_and_match_news() -> List[Dict[str, Any]]:
    """
    Agent 1 Execution:
    1. Fetches general market news.
    2. Runs targeted news searches for every registered stock.
    3. Maps articles, ranks by relevance, deduplicates, and limits output to top articles.
    4. Writes results to Firestore and clean_news.json.
    """
    logger.info("Agent 1: News Collector starting cycle.")
    
    # 1. Fetch general news feeds
    from app.data_sources.rss_scrapers import fetch_rss_articles
    raw_articles = fetch_rss_articles()
    
    ticker_map = load_ticker_map()
    
    # Fetch targeted news for all registered tickers
    targeted_articles = []
    for ticker, keywords in ticker_map.items():
        logger.info(f"Fetching targeted news for {ticker}...")
        t_news = fetch_targeted_news_for_stock(ticker, keywords)
        for art in t_news:
            art["matched_ticker"] = ticker
        targeted_articles.extend(t_news)
        time.sleep(0.2) # Polite delay
        
    # Merge and process
    all_news = []
    seen_urls = set()
    
    # Process targeted articles first
    for art in targeted_articles:
        url = art["url"]
        ticker = art["matched_ticker"]
        # Unique doc ID per URL + ticker
        doc_id = hashlib.md5(f"{url}_{ticker}".encode()).hexdigest()
        
        if doc_id in seen_urls:
            continue
            
        relevance = calculate_relevance_rank(art["title"], art["summary"], ticker_map[ticker], art["published_at"])
        
        clean_item = {
            "id": doc_id,
            "ticker": ticker,
            "title": art["title"],
            "url": url,
            "source": art["source"],
            "summary": art["summary"],
            "published_at": art["published_at"],
            "relevance_score": relevance,
            "collected_at": datetime.utcnow().isoformat() + "Z"
        }
        all_news.append(clean_item)
        seen_urls.add(doc_id)
        
    # Process general market articles
    for art in raw_articles:
        url = art["url"]
        title_lower = art["title"].lower()
        summary_lower = art["summary"].lower()
        
        matched_tickers = []
        for ticker, keywords in ticker_map.items():
            for kw in keywords:
                pattern = r'\b' + re.escape(kw.lower()) + r'\b'
                if re.search(pattern, title_lower) or re.search(pattern, summary_lower):
                    matched_tickers.append(ticker)
                    break
                    
        for ticker in matched_tickers:
            doc_id = hashlib.md5(f"{url}_{ticker}".encode()).hexdigest()
            if doc_id in seen_urls:
                continue
                
            relevance = calculate_relevance_rank(art["title"], art["summary"], ticker_map[ticker], art["published_at"])
            
            clean_item = {
                "id": doc_id,
                "ticker": ticker,
                "title": art["title"],
                "url": url,
                "source": art["source"],
                "summary": art["summary"],
                "published_at": art["published_at"],
                "relevance_score": relevance,
                "collected_at": datetime.utcnow().isoformat() + "Z"
            }
            all_news.append(clean_item)
            seen_urls.add(doc_id)
            
    # Rank by relevance and keep only top articles per ticker
    ranked_news = sorted(all_news, key=lambda x: x.get("relevance_score", 0.0), reverse=True)
    
    # Store and update in Firestore
    for item in ranked_news:
        try:
            db.collection("news").document(item["id"]).set(item, merge=True)
        except Exception as e:
            logger.error(f"Failed to store clean news article {item['id']} in Firestore: {e}")
            
    # Save to clean_news.json locally
    output_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "clean_news.json")
    try:
        with open(output_path, "w") as f:
            json.dump(ranked_news, f, indent=2)
        logger.info(f"Agent 1: News Collector finished. Saved {len(ranked_news)} ranked articles to {output_path}.")
    except Exception as e:
        logger.error(f"Failed writing clean_news.json: {e}")
        
    return ranked_news
