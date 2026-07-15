import os
import json
import logging
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any
import httpx

from app.db import db
from app.config import settings
from app.data_sources.market_data import get_market_data
from app.agents.alert_agent import record_telegram_audit

logger = logging.getLogger(__name__)

def track_predictions(top10_stocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Agent 7 Track: Registers Top 10 stocks as active predictions in Firestore 'prediction_history'.
    """
    logger.info("Learning Agent: Tracking new Top 10 predictions.")
    
    # 1. Fetch Nifty 50 Benchmark Current Price
    nifty_price = 22000.0 # fallback
    try:
        nifty_data = get_market_data("^NSEI")
        nifty_price = nifty_data.get("price", nifty_price)
    except Exception as e:
        logger.warning(f"Failed to fetch Nifty 50 price for prediction tracking: {e}")
        
    entry_time_str = datetime.utcnow().isoformat() + "Z"
    tracked = []
    
    # 2. Iterate Top 10 and add to prediction_history if not already active
    for stock in top10_stocks:
        ticker = stock["ticker"]
        
        # Check if an active prediction already exists for this ticker to avoid duplicates in the same run
        try:
            active_docs = db.collection("prediction_history") \
                            .where("ticker", "==", ticker) \
                            .where("status", "==", "active") \
                            .get()
            if active_docs:
                # Stock is already being tracked actively, skip creating a new prediction
                logger.debug(f"Ticker {ticker} is already active in prediction history. Skipping duplicate tracking.")
                continue
        except Exception as e:
            logger.warning(f"Error checking active predictions for {ticker}: {e}")
            
        doc_id = f"{ticker}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        prediction_doc = {
            "ticker": ticker,
            "company_name": stock.get("company_name", ticker),
            "score": int(stock.get("unified_score", 0)),
            "confidence": stock.get("confidence") or stock.get("ai_explanation", {}).get("confidence_level", "Medium"),
            "entry_price": float(stock.get("current_price", 0.0)),
            "entry_nifty": float(nifty_price),
            "entry_time": entry_time_str,
            "subscores": stock.get("subscores", {}),
            "milestones": {
                "1h": None,
                "4h": None,
                "1d": None,
                "7d": None,
                "30d": None
            },
            "status": "active"
        }
        
        try:
            db.collection("prediction_history").document(doc_id).set(prediction_doc)
            tracked.append(prediction_doc)
            logger.info(f"Registered prediction history tracking for {ticker} (Entry Price: ₹{prediction_doc['entry_price']}).")
        except Exception as e:
            logger.error(f"Failed to store prediction tracking for {ticker}: {e}")
            
    return tracked

def evaluate_predictions() -> List[Dict[str, Any]]:
    """
    Agent 7 Evaluate: Iterates active predictions, fetches milestone prices, and calculates performance returns.
    """
    logger.info("Learning Agent: Evaluating pending milestone predictions.")
    
    now = datetime.utcnow()
    evaluated = []
    
    # Milestone durations mapping
    milestone_durations = {
        "1h": timedelta(hours=1),
        "4h": timedelta(hours=4),
        "1d": timedelta(days=1),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30)
    }
    
    try:
        active_preds = db.collection("prediction_history").where("status", "==", "active").get()
        if not active_preds:
            logger.info("No active predictions pending evaluation.")
            return []
            
        for doc in active_preds:
            pred = doc.to_dict()
            doc_id = doc.id
            ticker = pred["ticker"]
            entry_time = datetime.fromisoformat(pred["entry_time"].replace("Z", ""))
            
            milestones = pred.get("milestones", {})
            updated = False
            
            # Check each milestone
            for m_name, duration in milestone_durations.items():
                if milestones.get(m_name) is None:
                    target_time = entry_time + duration
                    if now >= target_time:
                        # Milestone is due! Fetch current price and nifty
                        logger.info(f"Evaluating milestone {m_name} for {ticker} (Entry: {pred['entry_time']})")
                        
                        try:
                            # Stock price
                            stock_data = get_market_data(ticker)
                            curr_price = float(stock_data.get("price", 0.0))
                            
                            # Nifty price
                            nifty_data = get_market_data("^NSEI")
                            curr_nifty = float(nifty_data.get("price", 22000.0))
                            
                            if curr_price > 0:
                                stock_ret = ((curr_price - pred["entry_price"]) / pred["entry_price"]) * 100
                                nifty_ret = ((curr_nifty - pred["entry_nifty"]) / pred["entry_nifty"]) * 100
                                beat = stock_ret > nifty_ret
                                
                                milestones[m_name] = {
                                    "evaluated_at": now.isoformat() + "Z",
                                    "price": curr_price,
                                    "nifty": curr_nifty,
                                    "return": round(stock_ret, 2),
                                    "nifty_return": round(nifty_ret, 2),
                                    "beat": beat
                                }
                                updated = True
                                logger.info(f"Milestone {m_name} resolved for {ticker}: return {stock_ret:+.2f}% (Nifty: {nifty_ret:+.2f}%) | Beat: {beat}")
                        except Exception as e:
                            logger.error(f"Failed to evaluate milestone {m_name} for {ticker}: {e}")
                            
            if updated:
                # Check if all milestones are completed
                completed = all(milestones.get(m) is not None for m in milestone_durations)
                status = "completed" if completed else "active"
                
                db.collection("prediction_history").document(doc_id).update({
                    "milestones": milestones,
                    "status": status
                })
                pred["milestones"] = milestones
                pred["status"] = status
                evaluated.append(pred)
                
    except Exception as e:
        logger.error(f"Error querying active predictions: {e}")
        
    return evaluated

def calculate_and_save_stats() -> Dict[str, Any]:
    """
    Agent 7 Aggregate: Computes win rate, average returns, best/worst signals, and saves results in Firestore.
    """
    logger.info("Learning Agent: Aggregating prediction accuracy statistics.")
    
    total_milestones = 0
    wins = 0
    returns_sum = 0.0
    
    best_return = -999.0
    best_stock = "N/A"
    best_m = "N/A"
    
    worst_return = 999.0
    worst_stock = "N/A"
    worst_m = "N/A"
    
    total_signals = 0
    
    try:
        docs = db.collection("prediction_history").get()
        total_signals = len(docs)
        
        for doc in docs:
            pred = doc.to_dict()
            ticker = pred["ticker"]
            milestones = pred.get("milestones", {})
            
            for m_name, m_data in milestones.items():
                if m_data and "return" in m_data:
                    total_milestones += 1
                    ret = m_data["return"]
                    beat = m_data.get("beat", False)
                    
                    returns_sum += ret
                    if beat:
                        wins += 1
                        
                    if ret > best_return:
                        best_return = ret
                        best_stock = ticker
                        best_m = m_name
                    if ret < worst_return:
                        worst_return = ret
                        worst_stock = ticker
                        worst_m = m_name
                        
        win_rate = (wins / total_milestones * 100) if total_milestones > 0 else 0.0
        avg_ret = (returns_sum / total_milestones) if total_milestones > 0 else 0.0
        
        stats = {
            "win_rate": round(win_rate, 2),
            "average_return": round(avg_ret, 2),
            "best_stock": {
                "ticker": best_stock,
                "return": round(best_return, 2) if best_return != -999.0 else 0.0,
                "milestone": best_m
            },
            "worst_stock": {
                "ticker": worst_stock,
                "return": round(worst_return, 2) if worst_return != 999.0 else 0.0,
                "milestone": worst_m
            },
            "total_signals": total_signals,
            "total_evaluations": total_milestones,
            "updated_at": datetime.utcnow().isoformat() + "Z"
        }
        
        db.collection("learning_stats").document("current").set(stats)
        logger.info(f"Saved aggregated learning statistics: Win Rate {win_rate:.2f}%, Avg Return {avg_ret:+.2f}%.")
        return stats
        
    except Exception as e:
        logger.error(f"Error calculating learning stats: {e}")
        return {}

def optimize_weights() -> Dict[str, float]:
    """
    Agent 7 Weight Optimizer: Dynamically updates ranking weights based on factor performance.
    """
    logger.info("Learning Agent: Running dynamic weight optimization.")
    
    # Default Base weights
    weights = {
        "news_sentiment": 0.40,
        "technical_analysis": 0.30,
        "growth_potential": 0.20,
        "fundamentals": 0.10
    }
    
    try:
        docs = db.collection("prediction_history").get()
        if len(docs) < 5:
            logger.info("Insufficient historical records to run dynamic weight optimization (requires at least 5). Saving defaults.")
            db.collection("config").document("weights").set(weights)
            return weights
            
        score_adjustments = {k: 0.0 for k in weights}
        total_samples = 0
        
        for doc in docs:
            pred = doc.to_dict()
            subscores = pred.get("subscores", {})
            milestones = pred.get("milestones", {})
            
            for m_name, m_data in milestones.items():
                if m_data and "return" in m_data:
                    ret = m_data["return"]
                    nifty_ret = m_data.get("nifty_return", 0.0)
                    relative_performance = ret - nifty_ret
                    total_samples += 1
                    
                    # Reinforce factors: adjust weights based on subscore influence on returns
                    for factor in weights:
                         subscore_val = subscores.get(factor, 50.0) / 100.0 # Map 0-100 to 0-1
                         # If subscore was higher than median (0.5), we correlate it with returns.
                         # Positive return reinforces, negative return penalizes.
                         score_adjustments[factor] += (subscore_val - 0.5) * relative_performance
                         
        if total_samples > 0:
            for factor in weights:
                # Safe scaling step adjustment, clamped to max absolute adjustment of 0.15
                step = (score_adjustments[factor] / total_samples) * 0.05
                weights[factor] += max(-0.15, min(0.15, step))
                
            # Enforce limits: prevent weights from becoming too small or dominant
            for factor in weights:
                weights[factor] = max(0.05, min(0.60, weights[factor]))
                
            # Normalize to 1.0
            total_w = sum(weights.values())
            for factor in weights:
                weights[factor] = round(weights[factor] / total_w, 2)
                
            # Adjust rounding errors
            diff = round(1.0 - sum(weights.values()), 2)
            if diff != 0:
                weights["news_sentiment"] = round(weights["news_sentiment"] + diff, 2)
                
            logger.info(f"Dynamic weights adjusted: {weights}")
        
        db.collection("config").document("weights").set(weights)
        return weights
    except Exception as e:
        logger.error(f"Error optimizing ranking weights: {e}")
        db.collection("config").document("weights").set(weights)
        return weights

def send_weekly_report() -> bool:
    """
    Weekly Report: Dispatches compiled AI accuracy and performance stats to Telegram.
    """
    logger.info("Learning Agent: Generating and sending weekly Telegram performance report.")
    
    token = settings.telegram_bot_token
    chat_id = settings.telegram_chat_id
    
    if not token or not chat_id:
        logger.warning("Telegram configuration missing. Weekly report dispatch skipped.")
        record_telegram_audit("weekly_report", False, "", "Telegram credentials missing")
        return False
        
    try:
        # Load stats
        stats_doc = db.collection("learning_stats").document("current").get()
        if not stats_doc.exists:
            logger.warning("No learning statistics found in database. Weekly report skipped.")
            return False
            
        stats = stats_doc.to_dict()
        
        # Load weights
        weights_doc = db.collection("config").document("weights").get()
        weights = weights_doc.to_dict() if weights_doc.exists else {
            "news_sentiment": 0.40,
            "technical_analysis": 0.30,
            "growth_potential": 0.20,
            "fundamentals": 0.10
        }
        
        win_rate = stats.get("win_rate", 0.0)
        avg_ret = stats.get("average_return", 0.0)
        total_signals = stats.get("total_signals", 0)
        total_evals = stats.get("total_evaluations", 0)
        
        best = stats.get("best_stock", {})
        worst = stats.get("worst_stock", {})
        
        # Formulate HTML report
        timestamp_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        
        message = f"""📈 <b>WEEKLY AI ACCURACY REPORT</b>

<b>Dynamic Ranking Weights:</b>
• News Impact: {int(weights.get('news_sentiment', 0.4)*100)}%
• Technical Strength: {int(weights.get('technical_analysis', 0.3)*100)}%
• Volume Momentum: {int(weights.get('growth_potential', 0.2)*100)}%
• Company Quality: {int(weights.get('fundamentals', 0.1)*100)}%

<b>Performance Indicators:</b>
• Win Rate (vs NIFTY 50): <b>{win_rate:.2f}%</b>
• Average Return: <b>{avg_ret:+.2f}%</b>

• Best Signal: <b>{best.get('ticker', 'N/A')}</b> ({best.get('return', 0.0):+.2f}% in {best.get('milestone', 'N/A')})
• Worst Signal: <b>{worst.get('ticker', 'N/A')}</b> ({worst.get('return', 0.0):+.2f}% in {worst.get('milestone', 'N/A')})

• Signals Tracked: {total_signals}
• Evaluations run: {total_evals}

<i>Generated: {timestamp_str}</i>
<a href="{settings.resolved_dashboard_url}">Open Trading Dashboard</a>"""

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }
        
        response = httpx.post(url, json=payload, timeout=10.0)
        if response.status_code == 200:
            logger.info("Weekly Telegram performance report successfully sent.")
            record_telegram_audit("weekly_report", True, message)
            return True
        else:
            logger.error(f"Telegram API weekly report dispatch returned error {response.status_code}: {response.text}")
            record_telegram_audit("weekly_report", False, message, response.text)
            return False
            
    except Exception as e:
        logger.error(f"Error sending weekly Telegram report: {e}")
        record_telegram_audit("weekly_report", False, "", str(e))
        return False
