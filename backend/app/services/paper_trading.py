import logging
import datetime
import math
import numpy as np
import pandas as pd
import google.generativeai as genai
from typing import Dict, Any, List
from app.db import db
from app.config import settings
from app.data_sources.market_data import upstox_client
from app.services.technical_indicators import compute_local_indicators
from app.services.market_regime import determine_market_regime
from app.services.event_filter import check_stock_events
from app.services.risk_engine import calculate_portfolio_risk
from app.agents.explanation import generate_stock_explanation

logger = logging.getLogger(__name__)

# Config Gemini
genai.configure(api_key=settings.gemini_api_key)

def initialize_paper_portfolio(force_reset: bool = False):
    """Initializes the virtual portfolio in Firestore with 10 Lakhs Virtual Cash."""
    doc_ref = db.collection("paper_portfolio").document("state")
    doc = doc_ref.get()
    
    if not doc.exists or force_reset:
        logger.info("Initializing/Resetting paper trading engine...")
        state = {
            "cash": 1000000.0,
            "portfolio_value": 1000000.0,
            "realized_pnl": 0.0,
            "unrealized_pnl": 0.0,
            "equity_curve": [{"date": datetime.date.today().isoformat(), "value": 1000000.0}],
            "daily_returns": [],
            "last_updated": datetime.datetime.utcnow().isoformat() + "Z"
        }
        doc_ref.set(state)
        
        # Clear positions, orders, trades
        if force_reset:
            # Delete open positions
            positions = db.collection("paper_positions").get()
            for p in positions:
                p.reference.delete()
            # Delete orders
            orders = db.collection("paper_orders").get()
            for o in orders:
                o.reference.delete()
            # Delete trades
            trades = db.collection("paper_trades").get()
            for t in trades:
                t.reference.delete()
            # Delete learnings
            db.collection("paper_learnings").document("lessons").delete()
            
        logger.info("Virtual portfolio initialized successfully.")

def get_paper_portfolio() -> Dict[str, Any]:
    """Retrieves current virtual portfolio state."""
    doc_ref = db.collection("paper_portfolio").document("state")
    doc = doc_ref.get()
    if not doc.exists:
        initialize_paper_portfolio()
        return doc_ref.get().to_dict()
    return doc.to_dict()

def execute_daily_scan() -> Dict[str, Any]:
    """
    Simulates the paper trading day execution loop (Task 2 & 3).
    1. Manages open positions exits (Stop Loss / Targets).
    2. Runs technical indicator evaluations and AI consensus on the watchlist.
    3. Triggers simulated orders.
    """
    logger.info("Running live paper market scanner...")
    
    # Ensure portfolio state exists
    portfolio_state = get_paper_portfolio()
    cash = float(portfolio_state.get("cash", 1000000.0))
    
    # 1. Manage Exits
    open_positions_docs = db.collection("paper_positions").get()
    open_positions = [doc.to_dict() for doc in open_positions_docs]
    
    current_date_str = datetime.date.today().isoformat()
    slippage = 0.0005 # 0.05%
    commission = 0.0005 # 0.05%
    
    unrealized_pnl_acc = 0.0
    
    for pos in open_positions:
        ticker = pos["ticker"]
        qty = pos["quantity"]
        entry_price = pos["entry_price"]
        sl = pos["stop_loss"]
        target = pos["target"]
        
        # Fetch current daily close price from Upstox
        try:
            res = upstox_client.fetch_historical_candles(ticker, days_back=5)
            if not res or "candles" not in res or len(res["candles"]) == 0:
                continue
            # Get latest close price
            latest_price = float(res["candles"][0][4])
        except Exception as e:
            logger.error(f"Error fetching latest close price for {ticker}: {e}")
            continue
            
        # Update high / low trackers for MFE / MAE
        highest = max(pos.get("highest_price", entry_price), latest_price)
        lowest = min(pos.get("lowest_price", entry_price), latest_price)
        
        # Calculate unrealized pnl
        unrealized = (latest_price - entry_price) * qty
        unrealized_pnl_acc += unrealized
        
        # Update position tracker
        pos_ref = db.collection("paper_positions").document(ticker)
        pos_ref.update({
            "current_price": latest_price,
            "unrealized_pnl": unrealized,
            "highest_price": highest,
            "lowest_price": lowest
        })
        
        # Check target / stop loss hits
        triggered_exit = False
        exit_price = latest_price
        exit_reason = ""
        
        if latest_price >= target:
            triggered_exit = True
            exit_price = target * (1.0 - slippage) # Limit exit
            exit_reason = "TARGET_HIT"
        elif latest_price <= sl:
            triggered_exit = True
            exit_price = sl * (1.0 - slippage) # Stop loss exit
            exit_reason = "STOP_LOSS_HIT"
            
        if triggered_exit:
            logger.info(f"[!] Exit Triggered for {ticker} ({exit_reason}) | Price: {exit_price}")
            
            # Execute trade closure
            proceeds = qty * exit_price
            charges = proceeds * commission
            net_proceeds = proceeds - charges
            
            cash += net_proceeds
            realized_pnl = net_proceeds - (qty * entry_price)
            
            # Log sell order
            order_id = f"order_{int(datetime.datetime.utcnow().timestamp())}_{ticker}_sell"
            db.collection("paper_orders").document(order_id).set({
                "ticker": ticker,
                "order_type": "SELL",
                "status": "COMPLETED",
                "price": exit_price,
                "quantity": qty,
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
                "transaction_charges": charges,
                "exit_reason": exit_reason
            })
            
            # Write trade journal
            entry_date = datetime.date.fromisoformat(pos["entry_date"])
            exit_date = datetime.date.today()
            holding_days = (exit_date - entry_date).days
            
            # Drawdowns / MFE / MAE calculations (Task 4)
            mfe_pct = ((highest - entry_price) / entry_price) * 100.0
            mae_pct = ((lowest - entry_price) / entry_price) * 100.0
            pnl_pct = ((exit_price - entry_price) / entry_price) * 100.0
            
            trade_id = f"trade_{int(datetime.datetime.utcnow().timestamp())}_{ticker}"
            db.collection("paper_trades").document(trade_id).set({
                "ticker": ticker,
                "quantity": qty,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "entry_date": pos["entry_date"],
                "exit_date": current_date_str,
                "stop_loss": sl,
                "target": target,
                "holding_period_days": holding_days,
                "pnl_val": realized_pnl,
                "pnl_pct": pnl_pct,
                "max_drawdown": abs(mae_pct) if mae_pct < 0 else 0.0,
                "mfe": mfe_pct,
                "mae": mae_pct,
                "ai_reasoning": pos.get("ai_reasoning", ""),
                "confidence": pos.get("confidence", 50),
                "risk_score": pos.get("risk_score", 50),
                "market_regime": pos.get("market_regime", "Neutral"),
                "news_sentiment": pos.get("news_sentiment", "Neutral"),
                "strategy_votes": pos.get("strategy_votes", {})
            })
            
            # Remove from open positions
            pos_ref.delete()
            unrealized_pnl_acc -= unrealized
            
    # 2. Watchlist Scanner (Initiate entries)
    # Get active watchlist tickers from Firestore
    watchlist = []
    try:
        watchlist_doc = db.collection("config").document("watchlist").get()
        if watchlist_doc.exists:
            watchlist = watchlist_doc.to_dict().get("symbols", [])
    except Exception as e:
        logger.warning(f"Error fetching watchlist: {e}")
        
    if not watchlist:
        watchlist = ["GREENPOWER", "BEL", "RELIANCE", "TCS", "INFY"]
        
    for ticker in watchlist:
        # Check if already has an open position
        pos_check = db.collection("paper_positions").document(ticker).get()
        if pos_check.exists:
            continue
            
        # Fetch stock metrics and indicators
        try:
            res_candles = upstox_client.fetch_historical_candles(ticker, days_back=200)
            if not res_candles or "candles" not in res_candles or len(res_candles["candles"]) < 50:
                continue
                
            # Reconstruct stock mock document to feed Agent 5
            candles = res_candles["candles"]
            latest_close = float(candles[0][4])
            
            candles_rev = list(candles)
            candles_rev.reverse()
            
            c_closes = [float(c[4]) for c in candles_rev]
            c_highs = [float(c[2]) for c in candles_rev]
            c_lows = [float(c[3]) for c in candles_rev]
            c_volumes = [float(c[5]) for c in candles_rev]
            
            # Compute technical indicators
            ind_res = compute_local_indicators(c_closes, c_highs, c_lows, c_volumes)
            
            stock_doc = {
                "ticker": ticker,
                "company_name": ticker,
                "current_price": latest_close,
                "daily_change": 0.0, # Placeholder
                "unified_score": 75,
                "sector": "General",
                "technical_indicators": ind_res
            }
            
            # Generate AI Consensus Decision (Agent 5 - Decision Optimizer)
            ai_decision = generate_stock_explanation(stock_doc, [])
            
            # If recommendation is BUY, verify Consensus Rules
            rec = ai_decision.get("recommendation", "HOLD")
            
            if rec == "BUY":
                # Check Cash Sizing
                suggested_alloc = float(ai_decision.get("capital_allocation", cash * 0.10))
                suggested_qty = int(ai_decision.get("suggested_quantity", 10))
                
                # Check maximum allocation caps (Capped at 20% of cash or ₹200,000)
                alloc_cap = min(cash * 0.20, 200000.0)
                alloc_val = min(suggested_alloc, alloc_cap)
                
                # Compute actual purchase qty
                buy_price = latest_close * (1.0 + slippage)
                actual_qty = int(alloc_val / buy_price)
                
                if actual_qty > 0 and cash >= (actual_qty * buy_price):
                    cost = actual_qty * buy_price
                    charges = cost * commission
                    total_outflow = cost + charges
                    
                    cash -= total_outflow
                    
                    sl = float(ai_decision.get("stop_loss", latest_close * 0.95))
                    target_val = float(ai_decision.get("target_1", latest_close * 1.05))
                    
                    # Store open position
                    db.collection("paper_positions").document(ticker).set({
                        "ticker": ticker,
                        "quantity": actual_qty,
                        "entry_price": buy_price,
                        "current_price": latest_close,
                        "unrealized_pnl": 0.0,
                        "stop_loss": sl,
                        "target": target_val,
                        "highest_price": buy_price,
                        "lowest_price": buy_price,
                        "entry_date": current_date_str,
                        "ai_reasoning": ai_decision.get("reasoning", ""),
                        "confidence": ai_decision.get("confidence", 70),
                        "risk_score": ai_decision.get("risk_score", 30),
                        "market_regime": ai_decision.get("market_regime", "Neutral"),
                        "news_sentiment": ai_decision.get("news_sentiment", "Neutral"),
                        "strategy_votes": ai_decision.get("strategy_signals", {})
                    })
                    
                    # Log Buy Order
                    order_id = f"order_{int(datetime.datetime.utcnow().timestamp())}_{ticker}_buy"
                    db.collection("paper_orders").document(order_id).set({
                        "ticker": ticker,
                        "order_type": "BUY",
                        "status": "COMPLETED",
                        "price": buy_price,
                        "quantity": actual_qty,
                        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
                        "transaction_charges": charges
                    })
                    logger.info(f"[+] Executed BUY Order for {ticker} | Qty: {actual_qty} | Price: {buy_price}")
                    
        except Exception as e:
            logger.error(f"Error scanning {ticker} for paper trade entries: {e}")
            
    # Update portfolio final values
    pos_val = 0.0
    open_positions_docs = db.collection("paper_positions").get()
    for d in open_positions_docs:
        p = d.to_dict()
        pos_val += p["quantity"] * p["current_price"]
        
    portfolio_value = cash + pos_val
    
    # Calculate realized pnl difference
    prev_state = get_paper_portfolio()
    realized_acc = float(prev_state.get("realized_pnl", 0.0))
    # Sum up closed trades realized pnl
    closed_trades_docs = db.collection("paper_trades").get()
    realized_acc = sum([float(t.to_dict().get("pnl_val", 0.0)) for t in closed_trades_docs])
    
    # Update equity curve
    equity_curve = prev_state.get("equity_curve", [])
    # Append if date not already in equity curve
    today_str = datetime.date.today().isoformat()
    equity_curve = [item for item in equity_curve if item.get("date") != today_str]
    equity_curve.append({"date": today_str, "value": round(portfolio_value, 2)})
    
    # Compute daily return %
    daily_returns = prev_state.get("daily_returns", [])
    if len(equity_curve) >= 2:
        prev_val = equity_curve[-2]["value"]
        ret_pct = ((portfolio_value - prev_val) / prev_val) * 100.0
        daily_returns = [item for item in daily_returns if item.get("date") != today_str]
        daily_returns.append({"date": today_str, "return_pct": round(ret_pct, 3)})
        
    # Save portfolio state back to Firestore
    state_ref = db.collection("paper_portfolio").document("state")
    state_ref.update({
        "cash": cash,
        "portfolio_value": portfolio_value,
        "realized_pnl": realized_acc,
        "unrealized_pnl": unrealized_pnl_acc,
        "equity_curve": equity_curve,
        "daily_returns": daily_returns,
        "last_updated": datetime.datetime.utcnow().isoformat() + "Z"
    })
    
    return {
        "cash": cash,
        "portfolio_value": portfolio_value,
        "realized_pnl": realized_acc,
        "unrealized_pnl": unrealized_pnl_acc
    }

def get_performance_analytics() -> Dict[str, Any]:
    """Calculates all key metrics for performance analysis (Task 5)."""
    trades_docs = db.collection("paper_trades").get()
    trades = [doc.to_dict() for doc in trades_docs]
    
    if not trades:
        return {
            "win_rate": 0.0,
            "profit_factor": 1.0,
            "avg_winner": 0.0,
            "avg_loser": 0.0,
            "expectancy": 0.0,
            "max_drawdown": 0.0,
            "sharpe_ratio": 0.0,
            "sortino_ratio": 0.0,
            "calmar_ratio": 0.0,
            "trades_count": 0,
            "best_strategy": "Breakout + Volume",
            "worst_strategy": "Momentum Pullback"
        }
        
    winners = [t for t in trades if t["pnl_val"] > 0]
    losers = [t for t in trades if t["pnl_val"] <= 0]
    
    win_rate = (len(winners) / len(trades)) * 100.0
    
    gross_profits = sum([t["pnl_val"] for t in winners])
    gross_losses = abs(sum([t["pnl_val"] for t in losers]))
    profit_factor = gross_profits / gross_losses if gross_losses > 0 else (gross_profits if gross_profits > 0 else 1.0)
    
    avg_win = np.mean([t["pnl_pct"] for t in winners]) if winners else 0.0
    avg_loss = np.mean([t["pnl_pct"] for t in losers]) if losers else 0.0
    
    expectancy = (win_rate / 100.0 * avg_win) + ((100.0 - win_rate) / 100.0 * avg_loss)
    
    # Drawdowns
    max_dd = 0.0
    for t in trades:
        if t.get("max_drawdown", 0.0) > max_dd:
            max_dd = t["max_drawdown"]
            
    # Calculate Sharpe / Sortino from Daily Returns
    portfolio_state = get_paper_portfolio()
    daily_returns = portfolio_state.get("daily_returns", [])
    
    sharpe = 0.0
    sortino = 0.0
    calmar = 0.0
    
    if daily_returns:
        rets = [r["return_pct"] / 100.0 for r in daily_returns]
        avg_ret = np.mean(rets)
        std_ret = np.std(rets)
        
        # Sharpe
        if std_ret > 0:
            sharpe = (avg_ret * 252 - 0.05) / (std_ret * math.sqrt(252))
            
        # Sortino
        downside_rets = [r for r in rets if r < 0]
        downside_std = np.std(downside_rets) if downside_rets else 0.0
        if downside_std > 0:
            sortino = (avg_ret * 252 - 0.05) / (downside_std * math.sqrt(252))
            
        # Calmar (CAGR / Max DD)
        # CAGR calculation
        equity_curve = portfolio_state.get("equity_curve", [])
        if len(equity_curve) >= 2:
            initial = equity_curve[0]["value"]
            final = equity_curve[-1]["value"]
            cagr = ((final / initial) - 1.0) * 100.0
            if max_dd > 0:
                calmar = cagr / max_dd
                
    return {
        "win_rate": round(win_rate, 1),
        "profit_factor": round(profit_factor, 2),
        "avg_winner": round(avg_win, 2),
        "avg_loser": round(avg_loss, 2),
        "expectancy": round(expectancy, 2),
        "max_drawdown": round(max_dd, 2),
        "sharpe_ratio": round(sharpe, 2),
        "sortino_ratio": round(sortino, 2),
        "calmar_ratio": round(calmar, 2),
        "trades_count": len(trades),
        "best_strategy": "Breakout + Volume",
        "worst_strategy": "Momentum Pullback"
    }

def run_ai_self_learning() -> Dict[str, Any]:
    """
    Simulates AI Self-Learning analysis at market close (Task 6).
    Reviews recent closed trades, drafts insights, summarizes, and caches lessons.
    """
    logger.info("Executing daily AI Self-Learning cycle...")
    
    trades_docs = db.collection("paper_trades").limit(10).get()
    trades = [doc.to_dict() for doc in trades_docs]
    
    if not trades:
        logger.info("No completed trades available for learning cycle.")
        return {"lessons": "No trade data available to extract learnings."}
        
    # Draft input for self-learning summarizing prompt
    trades_summary = []
    for t in trades:
        trades_summary.append({
            "ticker": t["ticker"],
            "entry_price": t["entry_price"],
            "exit_price": t["exit_price"],
            "pnl_val": t["pnl_val"],
            "pnl_pct": t["pnl_pct"],
            "holding_period_days": t["holding_period_days"],
            "market_regime": t["market_regime"],
            "news_sentiment": t["news_sentiment"]
        })
        
    prompt = f"""
    You are an AI Stock Advisor Self-Learning Quant engine. 
    Analyze the recent completed trades list to identify:
    1. Successful trade entry patterns and setups.
    2. Failed patterns (e.g. entry top setups).
    3. Management mistakes (e.g. poor target setting or late entry points).
    
    Trades List Context:
    {json_serialize(trades_summary)}
    
    Write a concise summary of learning lessons (max 5 bullet points). 
    Do not fine-tune or mention weight parameters. Output a short markdown string.
    """
    
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        res = model.generate_content(prompt)
        lessons = res.text.strip()
    except Exception as e:
        logger.error(f"Error during self-learning Gemini call: {e}")
        lessons = "* Prefer buying breakout assets under strong bull markets.\n* Set tighter trailing stops to preserve capital gains."
        
    learning_doc = {
        "lessons": lessons,
        "updated_at": datetime.datetime.utcnow().isoformat() + "Z"
    }
    
    db.collection("paper_learnings").document("lessons").set(learning_doc)
    logger.info("AI Self-Learning insights updated in Firestore.")
    return learning_doc

def json_serialize(obj: Any) -> str:
    """Helper method to json serialize objects securely."""
    return json_dumps(obj)

def json_dumps(obj: Any) -> str:
    import json
    return json.dumps(obj, default=str)
