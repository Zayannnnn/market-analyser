import logging
import feedparser
import re
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Keywords indicating upcoming high-uncertainty events or board meetings
EVENT_KEYWORDS = [
    r"\bearnings\b",
    r"\board\s+meeting\b",
    r"\bdividend\b",
    r"\bstock\s+split\b",
    r"\bbonus\s+issue\b",
    r"\bq[1-4]\s+results\b",
    r"\bfinancial\s+results\b",
    r"\bacquisition\b",
    r"\bmerger\b",
    r"\brights\s+issue\b"
]

import urllib.parse

def check_stock_events(ticker: str, company_name: str) -> Dict[str, Any]:
    """
    Agent 4 Event Filter: Scrapes targeted news search feeds for upcoming board meetings,
    earnings calls, or corporate actions in the next 7 days.
    """
    logger.info(f"Checking upcoming corporate events and actions for {ticker}...")
    
    result = {
        "upcoming_event_detected": False,
        "event_type": None,
        "details": None
    }
    
    # Query Google News RSS for earnings/board meetings specifically
    query = f'"{ticker}" AND ("earnings" OR "board meeting" OR "dividend" OR "results")'
    encoded_query = urllib.parse.quote_plus(query)
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-IN&gl=IN&ceid=IN:en"
    
    try:
        feed = feedparser.parse(url)
        if not feed.entries:
            return result
            
        detected_details = []
        for entry in feed.entries[:5]:  # Check top 5 news matches
            title = entry.get("title", "")
            title_lower = title.lower()
            
            # Check if any keyword matches
            for kw in EVENT_KEYWORDS:
                if re.search(kw, title_lower):
                    # Flag as upcoming event if title suggests "announces", "declares", "meeting", "on", "dates", etc.
                    indicator_words = ["announces", "declares", "meeting", "on", "schedule", "this week", "next week", "date"]
                    if any(w in title_lower for w in indicator_words):
                        detected_details.append(title.split(" - ")[0])
                        break
                        
        if detected_details:
            result["upcoming_event_detected"] = True
            result["event_type"] = "Corporate Event/Action"
            result["details"] = "; ".join(detected_details[:2])
            logger.info(f"[!] Upcoming Event Detected for {ticker}: {result['details']}")
            
    except Exception as e:
        logger.error(f"Error checking upcoming corporate events for {ticker}: {e}")
        
    return result
