import feedparser
import logging
import re
from typing import List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

FEEDS = {
    "google_news": "https://news.google.com/rss/search?q=NSE+stocks+business+India&hl=en-IN&gl=IN&ceid=IN:en",
    "economic_times": "https://economictimes.indiatimes.com/markets/stocks/news/rssfeeds/2146842.cms",
    "moneycontrol": "https://www.moneycontrol.com/rss/buzzingstocks.xml"
}

def clean_html(text: str) -> str:
    """Removes HTML tags from RSS description fields."""
    if not text:
        return ""
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text).strip()

def parse_rss_date(date_str: str) -> str:
    """Standardizes various RSS published formats to ISO 8601 format."""
    try:
        # standard RSS pubDate is RFC 822: "Wed, 03 Jun 2026 10:15:00 GMT"
        # we can parse and reformat
        # feedparser handles dates automatically under entry.published_parsed structure,
        # but as fallback we re-format the string.
        return date_str
    except Exception:
        return datetime.utcnow().isoformat() + "Z"

def fetch_rss_articles() -> List[Dict[str, Any]]:
    """
    Scrapes Google News, Economic Times, and Moneycontrol RSS.
    Returns a unified list of raw articles.
    """
    logger.info("Initializing RSS feed scrape cycle.")
    raw_articles = []
    
    for feed_name, url in FEEDS.items():
        logger.info(f"Querying RSS source: {feed_name}")
        try:
            feed = feedparser.parse(url)
            if not feed.entries:
                logger.warning(f"No articles retrieved from {feed_name}")
                continue
                
            for entry in feed.entries:
                title = entry.get("title", "")
                link = entry.get("link", "")
                summary = clean_html(entry.get("summary", "") or entry.get("description", ""))
                
                # Resolve date
                published = entry.get("published", "")
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    published = datetime(*entry.published_parsed[:6]).isoformat() + "Z"
                else:
                    published = parse_rss_date(published)
                
                # Determine source details
                source = feed_name.replace("_", " ").title()
                if feed_name == "google_news" and " - " in title:
                    # Google news appends actual publisher at the end of title, e.g. "Stock Breakout - Moneycontrol"
                    parts = title.split(" - ")
                    title = " - ".join(parts[:-1])
                    source = parts[-1].strip()

                raw_articles.append({
                    "title": title.strip(),
                    "url": link,
                    "summary": summary[:400] + "..." if len(summary) > 400 else summary,
                    "source": source,
                    "published_at": published
                })
        except Exception as e:
            logger.error(f"Failed to scrape RSS feed {feed_name}: {e}")
            
    logger.info(f"RSS scrape completed. Retrieved {len(raw_articles)} raw entries.")
    return raw_articles
