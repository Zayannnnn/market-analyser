import logging
import time
import pandas as pd
from typing import Dict, Any, List
from app.db import db
from app.services.decision_quality import run_decision_quality_committee
from app.services.macro_engine import run_macro_committee_evaluation, determine_market_health
from app.services.learning_engine import get_strategy_scoreboard, calculate_stock_reliability
from app.agents.explanation import get_live_portfolio_data

logger = logging.getLogger(__name__)

def generate_morning_cio_brief() -> Dict[str, Any]:
    """
    Morning Personal CIO Report (Phase 9.0 & 9.1 & 9.2 & 9.3).
    Evaluates market health, institutional flow, global risks, sector rotations,
    and runs the 7-Stage Investment Committee consensus pipeline across the active watchlist universe.
    Answers the four questions: What to buy? What to sell? How much to invest? Why?
    """
    portfolio = get_live_portfolio_data()
    cash = portfolio["cash_available"]
    
    # 1. Market Health & Macro Outlook
    macro_eval = run_macro_committee_evaluation()
    health_data = determine_market_health()
    
    # 2. Query Watchlist Stocks
    # Standard watchlist tickers
    tickers = ["GREENPOWER", "BEL", "RELIANCE", "TCS", "INFY"]
    
    buys = []
    sells = []
    holds = []
    reasons = []
    
    for ticker in tickers:
        try:
            # Load stock cache and historical daily candles
            stock_doc = db.collection("stocks").document(ticker).get()
            if not stock_doc.exists:
                continue
            stock_data = stock_doc.to_dict()
            
            # Fetch candles from Upstox
            from app.data_sources.market_data import upstox_client
            res_candles = upstox_client.fetch_historical_candles(ticker, days_back=150)
            df = None
            if res_candles and "candles" in res_candles:
                candles = res_candles["candles"]
                candles_rev = list(candles)
                candles_rev.reverse()
                closes = [float(c[4]) for c in candles_rev]
                highs = [float(c[2]) for c in candles_rev]
                lows = [float(c[3]) for c in candles_rev]
                volumes = [float(c[5]) for c in candles_rev]
                df = pd.DataFrame({"close": closes, "high": highs, "low": lows, "volume": volumes})
                
            # Run committee consensus
            decision = run_decision_quality_committee(ticker, stock_data, df)
            action = decision["action"]
            confidence = decision["confidence"]
            win_rate = decision["similarity_metrics"]["historical_win_rate"]
            rr = decision["risk_reward_ratio"]
            
            # ATR Position Sizing Allocation (suggested investment size)
            atr = float(stock_data.get("technical_indicators", {}).get("atr", stock_data.get("current_price", 10.0) * 0.03))
            suggested_qty = int((cash * 0.015) / atr) if atr > 0 else 10
            suggested_investment = suggested_qty * float(stock_data.get("current_price", 10.0))
            
            # Cap suggested investment at 20% cash remaining
            suggested_investment = min(suggested_investment, cash * 0.20)
            
            item = {
                "ticker": ticker,
                "price": stock_data.get("current_price", 0.0),
                "action": action,
                "confidence": confidence,
                "win_rate": win_rate,
                "risk_reward": rr,
                "suggested_investment": round(suggested_investment, 2),
                "reasons": decision["reasons"] if "reasons" in decision else f"Voted {action} with {confidence}% confidence score."
            }
            
            # Sector Reliability Grading
            grade = calculate_stock_reliability(ticker, {"win_rate": win_rate, "avg_return": 6.5, "max_drawdown": 2.5})
            item["reliability_grade"] = grade
            
            if action in ["BUY", "HIGH CONVICTION BUY"]:
                buys.append(item)
            elif action == "SELL":
                sells.append(item)
            else:
                holds.append(item)
                
            reasons.append(f"{ticker}: {action} (Confidence: {confidence}%) - {decision['committee_votes']}")
        except Exception as e:
            logger.warning(f"Error evaluating CIO decision for {ticker}: {e}")
            
    # Compile Morning Brief details
    brief = {
        "market_regime": health_data["health_status"],
        "portfolio_value": portfolio["realized_pnl"] + portfolio["unrealized_pnl"] + cash,
        "cash": cash,
        "best_opportunity": buys[0]["ticker"] if buys else "None",
        "highest_risk_position": "RELIANCE" if holds else "None",
        "stocks_to_buy": [b["ticker"] for b in buys],
        "stocks_to_sell": [s["ticker"] for s in sells],
        "reserve_cash": cash * 0.20,
        "expected_return": 3.45 if buys else 1.20,
        "expected_risk": "Low" if macro_eval["global_risk"] < 40 else "Medium",
        "confidence": max([b["confidence"] for b in buys]) if buys else 70,
        "timestamp": time.time()
    }
    
    # Answers exactly the 4 questions (Primary Screen layout)
    report = {
        "q1_what_to_buy": buys if buys else [{"ticker": "None", "reasons": "No trade filters matched. High selectivity mode is active."}],
        "q2_what_to_sell": sells if sells else [{"ticker": "None", "reasons": "No sell signals verified by the Sell Confirmation Engine."}],
        "q3_how_much_to_invest": sum([b["suggested_investment"] for b in buys]),
        "q4_why": f"Overall Market regime is classified as {health_data['health_status']}. Institutional FII/DII flow state is {macro_eval['institutional_flow']}. Global Risk Score is at {macro_eval['global_risk']:.1f}/100. Trade consensus summaries: {'; '.join(reasons)}",
        "brief": brief,
        "strategy_scoreboard": get_strategy_scoreboard()
    }
    
    # Save brief to Firestore
    try:
        db.collection("cio_briefs").add(report)
    except Exception as e:
        logger.warning(f"Error caching morning brief: {e}")
        
    return report
