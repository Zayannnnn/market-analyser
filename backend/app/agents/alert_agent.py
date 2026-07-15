import logging
import httpx
import os
import json
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
from app.config import settings
from app.db import db

logger = logging.getLogger(__name__)

def record_telegram_audit(kind: str, success: bool, message: str = "", error: str = "") -> None:
    try:
        doc_id = f"{kind}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}"
        db.collection("telegram_audit").document(doc_id).set({
            "kind": kind,
            "success": success,
            "message": message[:500],
            "error": error[:500],
            "timestamp": datetime.utcnow().isoformat() + "Z",
        })
    except Exception as exc:
        logger.error(f"Failed writing Telegram audit event: {exc}")

def check_duplicate_alert(ticker: str) -> bool:
    """Checks if an alert was already sent for this stock ticker in the last 24 hours."""
    try:
        limit_time = datetime.utcnow() - timedelta(hours=24)
        limit_time_str = limit_time.isoformat() + "Z"
        
        alerts_ref = db.collection("alerts") \
                       .where("ticker", "==", ticker) \
                       .where("timestamp", ">=", limit_time_str) \
                       .get()
        return len(alerts_ref) > 0
    except Exception as e:
        logger.error(f"Error checking duplicate alerts for {ticker}: {e}")
        return False

def check_daily_alert_limit() -> bool:
    """Checks if the global limit of 10 alerts per day has been reached."""
    try:
        # Get start of today (UTC)
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_start_str = today_start.isoformat() + "Z"
        
        alerts_ref = db.collection("alerts") \
                       .where("timestamp", ">=", today_start_str) \
                       .get()
        return len(alerts_ref) >= settings.max_alerts_per_day
    except Exception as e:
        logger.error(f"Error checking daily alert limits: {e}")
        return False

def trigger_telegram_alert(stock: Dict[str, Any], avg_sentiment: float) -> bool:
    """
    Sends an HTML formatted alert to Telegram chat/channel when score exceeds 75.
    """
    token = settings.telegram_bot_token
    chat_id = settings.telegram_chat_id
    
    if not token or not chat_id:
        logger.warning("Telegram Bot Credentials missing. Skipping notification dispatch.")
        record_telegram_audit("stock_alert", False, stock["ticker"], "Telegram credentials missing")
        return False
        
    ticker = stock["ticker"]
    company_name = stock.get("company_name", ticker)
    score = stock.get("unified_score", 0)
    ai_exp = stock.get("ai_explanation", {})
    
    why_ranked = ai_exp.get("why_ranked", "Ranked highly based on technical strength and high sentiment scores.")
    
    # Retrieve news summary from Firestore for this ticker
    news_summary = "No recent news summaries collected."
    try:
        news_docs = db.collection("news").where("ticker", "==", ticker).get()
        if news_docs:
            # Sort news by published_at descending
            sorted_docs = sorted(news_docs, key=lambda x: x.to_dict().get("published_at", ""), reverse=True)
            latest_news = sorted_docs[0].to_dict()
            title = latest_news.get("title", "Headline Unavailable")
            summary = latest_news.get("summary", "Summary Unavailable")
            news_summary = f"<b>{title}</b>\n{summary}"
    except Exception as e:
        logger.warning(f"Failed to fetch news summary for alert message for {ticker}: {e}")
        
    timestamp_now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    
    message = f"""🚀 <b>AORA ENGINE - INSIGHT DETECTED</b>

<b>Ticker:</b> {ticker} ({company_name})
<b>AI Score:</b> {score}/100

<b>AI Rationale:</b>
{why_ranked}

<b>News Summary:</b>
{news_summary}

<i>Generated: {timestamp_now}</i>
<a href="{settings.resolved_dashboard_url}">Open AORA Engine Terminal</a>"""

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    
    try:
        response = httpx.post(url, json=payload, timeout=12.0)
        if response.status_code == 200:
            logger.info(f"Telegram alert successfully sent for stock ticker: {ticker}")
            record_telegram_audit("stock_alert", True, message)
            return True
        else:
            logger.error(f"Telegram API returned error status {response.status_code}: {response.text}")
            record_telegram_audit("stock_alert", False, message, response.text)
            return False
    except Exception as e:
        logger.error(f"HTTP request error sending Telegram alert for {ticker}: {e}")
        record_telegram_audit("stock_alert", False, ticker, str(e))
        return False

def run_alert_agent(analyzed_top10: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Agent 6 Execution: Evaluates trigger criteria for Top 10 stocks.
    Triggers Telegram notifications when unified_score > 75 and creates log entries.
    """
    logger.info("Agent 6: Smart Alert Agent starting opportunity scans.")
    sent_alerts = []
    
    # 1. Enforce global rate limit (Max 10 alerts per day)
    if check_daily_alert_limit():
        logger.warning(f"Global daily alert limit ({settings.max_alerts_per_day}) hit. Notifications suspended for this cycle.")
        return []
        
    for stock in analyzed_top10:
        ticker = stock["ticker"]
        score = stock.get("unified_score", 0)
        ai_exp = stock.get("ai_explanation", {})
        
        # Calculate average news sentiment score for logging
        avg_sentiment = 0.0
        try:
            news_docs = db.collection("news").where("ticker", "==", ticker).get()
            if news_docs:
                avg_sentiment = sum(d.to_dict().get("sentiment_score", 0.0) for d in news_docs) / len(news_docs)
        except Exception as e:
            logger.warning(f"Failed to calculate news sentiment average for alert validation: {e}")
            
        confidence = ai_exp.get("confidence_level", "Medium")
        
        # Trigger validation: Score exceeds 75
        criteria_met = (score > 75)
        
        if criteria_met:
            logger.info(f"Target opportunities identified for {ticker} (Score: {score}). Validating cooldown limits.")
            
            # Check duplicate alerts in 24h
            if check_duplicate_alert(ticker):
                logger.info(f"Duplicate alert skipped. Alert was already dispatched for {ticker} in the last 24 hours.")
                continue
                
            # Fire alert!
            success = trigger_telegram_alert(stock, avg_sentiment)
            
            if success:
                # Save alert snapshot in Firestore
                alert_doc = {
                    "ticker": ticker,
                    "company_name": stock.get("company_name", ticker),
                    "score": float(score),
                    "confidence": confidence,
                    "sentiment_score": float(avg_sentiment),
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "alert_sent": True
                }
                
                try:
                    alert_id = f"{ticker}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
                    db.collection("alerts").document(alert_id).set(alert_doc)
                    sent_alerts.append(alert_doc)
                except Exception as e:
                    logger.error(f"Failed to store alert logging inside Firestore alerts: {e}")
                    
                # Re-check daily limit after sending, stop if limit is reached
                if check_daily_alert_limit():
                    logger.info("Daily alert limit reached mid-cycle. Halting scan.")
                    break
                    
    logger.info(f"Agent 6 scan finished. Alert notifications dispatched: {len(sent_alerts)}.")
    return sent_alerts

def send_daily_close_report() -> bool:
    """
    At market close (15:30 IST / 10:00 UTC), sends a Telegram message containing:
    Top 10 stocks, scores, rankings, reason for ranking.
    """
    logger.info("Daily Close Report: Generating and sending market close report to Telegram.")
    token = settings.telegram_bot_token
    chat_id = settings.telegram_chat_id
    
    if not token or not chat_id:
        logger.warning("Telegram configuration missing. Daily close report dispatch skipped.")
        record_telegram_audit("daily_close", False, "", "Telegram credentials missing")
        return False
        
    try:
        # Fetch current Top 10 rankings
        rank_doc = db.collection("rankings").document("current").get()
        if not rank_doc.exists:
            logger.warning("No current rankings found in database. Attempting to fetch top10.json fallback.")
            local_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "top10.json")
            if os.path.exists(local_path):
                with open(local_path, "r") as f:
                    top10_list = json.load(f)
            else:
                logger.warning("No rankings data available for daily close report.")
                return False
        else:
            top10_list = rank_doc.to_dict().get("top_10", [])
            
        if not top10_list:
            logger.warning("Top 10 list is empty. Skipping report.")
            return False
            
        # Pre-fetch AI explanations for reasons
        ai_dict = {}
        try:
            ai_docs = db.collection("ai_analysis").get()
            for doc in ai_docs:
                ai_dict[doc.id] = doc.to_dict()
        except Exception as e:
            logger.warning(f"Error fetching AI explanations for daily report: {e}")
            
        timestamp_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        
        message_lines = [
            f"🔔 <b>AORA ENGINE - DAILY MARKET CLOSE REPORT</b>",
            f"<i>Date: {timestamp_str} (IST Close)</i>",
            f"",
            f"Here are the Top 10 stocks analyzed and ranked by the AORA Engine:",
            f""
        ]
        
        for i, stock in enumerate(top10_list[:10]):
            ticker = stock.get("ticker", "")
            company = stock.get("company_name", ticker)
            score = stock.get("unified_score", 0)
            
            # Fetch AI reason
            ai_data = ai_dict.get(ticker) or {}
            reason = ai_data.get("why_ranked", "Ranked highly based on technical and volume momentum indicators.")
            
            message_lines.append(f"<b>{i+1}. {ticker} ({company})</b>")
            message_lines.append(f"• Score: <b>{score}/100</b>")
            message_lines.append(f"• AI Reason: {reason}")
            message_lines.append(f"")
            
        message_lines.append(f"<a href=\"{settings.resolved_dashboard_url}\">Access AORA Engine Terminal</a>")
        message_text = "\n".join(message_lines)
        
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message_text,
            "parse_mode": "HTML"
        }
        
        response = httpx.post(url, json=payload, timeout=12.0)
        if response.status_code == 200:
            logger.info("Daily close Telegram report successfully sent.")
            record_telegram_audit("daily_close", True, message_text)
            return True
        else:
            logger.error(f"Telegram API daily close report returned error {response.status_code}: {response.text}")
            record_telegram_audit("daily_close", False, message_text, response.text)
            return False
            
    except Exception as e:
        logger.error(f"Error sending daily market close report: {e}")
        record_telegram_audit("daily_close", False, "", str(e))
        return False

def send_user_telegram_notification(user_id: str, ticker: str, company_name: str, current_score: int, target_score: int, price: str) -> bool:
    """
    Dispatches a Telegram message to notify a user that their custom target score alert has been hit.
    """
    token = settings.telegram_bot_token
    chat_id = settings.telegram_chat_id
    
    if not token or not chat_id:
        logger.warning("Telegram Bot Credentials missing. Skipping user alert notification.")
        record_telegram_audit("user_alert", False, ticker, "Telegram credentials missing")
        return False
        
    message = f"""🔔 <b>AORA ENGINE - USER ALERT TRIGGERED</b>
    
An active stock intelligence alert has reached its target score!

<b>User ID:</b> {user_id}
<b>Ticker:</b> {ticker} ({company_name})
<b>Current Price:</b> {price}
<b>Current AI Score:</b> {current_score}/100
<b>Target AI Score:</b> {target_score}/100

<i>This alert is now marked as completed.</i>
<a href="{settings.resolved_dashboard_url}">Open AORA Engine Terminal</a>"""

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    
    try:
        response = httpx.post(url, json=payload, timeout=12.0)
        if response.status_code == 200:
            logger.info(f"User alert Telegram notification successfully sent for user {user_id} on {ticker}")
            record_telegram_audit("user_alert", True, message)
            return True
        else:
            logger.error(f"Telegram API returned error status {response.status_code}: {response.text}")
            record_telegram_audit("user_alert", False, message, response.text)
            return False
    except Exception as e:
        logger.error(f"HTTP request error sending user Telegram notification: {e}")
        record_telegram_audit("user_alert", False, ticker, str(e))
        return False

def check_user_alerts():
    """
    Queries active user alerts in Firestore. Checks if the corresponding
    stock scores meet the target threshold, and fires Telegram notifications.
    """
    try:
        active_alerts_ref = db.collection("user_alerts").where("status", "==", "active").get()
        if not active_alerts_ref:
            return
            
        logger.info(f"Checking {len(active_alerts_ref)} active user alerts against updated scores...")
        
        for doc in active_alerts_ref:
            alert = doc.to_dict()
            alert_id = doc.id
            ticker = alert.get("ticker")
            target_score = alert.get("target_score")
            user_id = alert.get("user_id")
            
            # Fetch current stock score from Firestore stocks collection
            stock_doc = db.collection("stocks").document(ticker).get()
            if not stock_doc.exists:
                logger.warning(f"Stock ticker {ticker} not found for user alert checking.")
                continue
                
            stock_data = stock_doc.to_dict()
            current_score = stock_data.get("unified_score", 0)
            company_name = stock_data.get("company_name", ticker)
            current_price = stock_data.get("current_price", 0.0)
            formatted_price = f"₹{current_price:,.2f}" if isinstance(current_price, (int, float)) else str(current_price)
            
            if current_score >= target_score:
                logger.info(f"Target threshold met for user alert {alert_id} (Current: {current_score} >= Target: {target_score})")
                
                # Send Telegram alert
                success = send_user_telegram_notification(user_id, ticker, company_name, current_score, target_score, formatted_price)
                if success:
                    # Update status to completed
                    db.collection("user_alerts").document(alert_id).update({
                        "status": "completed",
                        "completed_at": datetime.utcnow().isoformat() + "Z",
                        "triggered_score": float(current_score)
                    })
    except Exception as e:
        logger.error(f"Error checking user alerts: {e}")
