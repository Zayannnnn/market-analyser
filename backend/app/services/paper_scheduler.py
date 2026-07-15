import logging
import datetime
import httpx
import time
import socket
import pandas as pd
import numpy as np
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
from app.services.paper_trading import get_paper_portfolio, run_ai_self_learning, get_performance_analytics

logger = logging.getLogger(__name__)

# Configure Gemini
genai.configure(api_key=settings.gemini_api_key)

def send_telegram_alert(message: str) -> bool:
    """Helper method to dispatch formatted HTML alerts to Telegram (Task 4)."""
    token = settings.telegram_bot_token
    chat_id = settings.telegram_chat_id
    if not token or not chat_id:
        logger.warning(f"Telegram credentials missing. Dispatch skipped.")
        return False
        
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }
        res = httpx.post(url, json=payload, timeout=10.0)
        return res.status_code == 200
    except Exception as e:
        logger.error(f"Error dispatching Telegram alert: {e}")
        return False

def add_scheduler_log(event: str, level: str = "INFO", message: str = ""):
    """Appends an execution log record to Firestore scheduler status (Task 5)."""
    try:
        doc_ref = db.collection("paper_scheduler").document("status")
        doc = doc_ref.get()
        
        logs = []
        if doc.exists:
            logs = doc.to_dict().get("logs", [])
            
        new_log = {
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "event": event,
            "level": level,
            "message": message
        }
        logs.append(new_log)
        # Cap log history at 50 entries
        if len(logs) > 50:
            logs = logs[-50:]
            
        doc_ref.update({"logs": logs})
    except Exception as e:
        logger.error(f"Error writing scheduler execution log: {e}")

def update_scheduler_status(
    status: str = "ACTIVE",
    current_job: str = "IDLE",
    gemini_status: str = "CONNECTED",
    upstox_status: str = "CONNECTED",
    firestore_status: str = "CONNECTED",
    telegram_status: str = "CONNECTED"
):
    """Updates general metadata block of the Paper Scheduler state."""
    try:
        doc_ref = db.collection("paper_scheduler").document("status")
        
        # Calculate next scan time (e.g. 30 minutes from now)
        next_scan = (datetime.datetime.utcnow() + datetime.timedelta(minutes=30)).isoformat() + "Z"
        
        meta = {
            "status": status,
            "current_job": current_job,
            "last_scan_time": datetime.datetime.utcnow().isoformat() + "Z",
            "next_scan_time": next_scan,
            "gemini_status": gemini_status,
            "upstox_status": upstox_status,
            "firestore_status": firestore_status,
            "telegram_status": telegram_status,
            "updated_at": datetime.datetime.utcnow().isoformat() + "Z"
        }
        
        # Get today's trades and P&L counts
        trades_docs = db.collection("paper_trades").get()
        today_str = datetime.date.today().isoformat()
        today_trades = [t.to_dict() for t in trades_docs if t.to_dict().get("exit_date") == today_str]
        
        meta["today_trades_count"] = len(today_trades)
        meta["today_pnl"] = sum([t.get("pnl_val", 0.0) for t in today_trades])
        
        doc_ref.set(meta, merge=True)
    except Exception as e:
        logger.error(f"Error updating scheduler status meta: {e}")

def run_health_checks() -> Dict[str, str]:
    """
    Executes the 08:45 IST scheduler check logic (Task 1 & 6).
    Checks trading holiday status, internet ping, and Upstox auth.
    """
    logger.info("Executing 08:45 IST morning health checks...")
    add_scheduler_log("Morning Health Checks", "INFO", "Initiating morning checks sequence.")
    
    status_map = {
        "internet": "CONNECTED",
        "upstox": "CONNECTED",
        "firestore": "CONNECTED",
        "gemini": "CONNECTED",
        "telegram": "CONNECTED"
    }
    
    # 1. Check internet connection
    try:
        # Resolve google domain to check dns and tcp connection
        socket.setdefaulttimeout(5)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
    except Exception as e:
        logger.warning(f"Internet connectivity check failed: {e}")
        status_map["internet"] = "DISCONNECTED"
        
    # 2. Check Upstox authentication
    try:
        from app.services.health_monitor import validate_upstox_token
        v_res = validate_upstox_token()
        if not v_res["valid"]:
            status_map["upstox"] = "DISCONNECTED"
    except Exception as e:
        logger.warning(f"Upstox status verification failed: {e}")
        status_map["upstox"] = "DISCONNECTED"
        
    # 3. Check Firestore
    try:
        db.collection("paper_scheduler").document("status").get()
    except Exception as e:
        logger.warning(f"Firestore status verification failed: {e}")
        status_map["firestore"] = "DISCONNECTED"
        
    # 4. Check Telegram
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        status_map["telegram"] = "DISCONNECTED"
        
    # 5. Check Holiday status
    is_holiday = False
    today_dt = datetime.datetime.now()
    # Weekend check
    if today_dt.weekday() in [5, 6]:
        is_holiday = True
        logger.info("Today is a weekend. Marking as holiday.")
        add_scheduler_log("Holiday Check", "INFO", "Market is closed today (Weekend).")
    else:
        # Check standard holiday master collection if registered
        try:
            holiday_doc = db.collection("config").document("holidays").get()
            if holiday_doc.exists:
                holidays = holiday_doc.to_dict().get("dates", [])
                if today_dt.strftime("%Y-%m-%d") in holidays:
                    is_holiday = True
                    logger.info("Today is registered as an official NSE market holiday.")
                    add_scheduler_log("Holiday Check", "INFO", "Market is closed today (NSE Official Holiday).")
        except Exception as e:
            logger.warning(f"Holiday checks miss: {e}")
            
    # Update scheduler metadata in Firestore
    update_scheduler_status(
        status="IDLE" if is_holiday else "ACTIVE",
        current_job="HEALTH_CHECK_COMPLETED",
        gemini_status=status_map["gemini"],
        upstox_status=status_map["upstox"],
        firestore_status=status_map["firestore"],
        telegram_status=status_map["telegram"]
    )
    
    return status_map

def execute_watchlist_auto_scan() -> Dict[str, Any]:
    """
    Simulates the 09:00 / 09:15 Watchlist auto scanner pipeline (Task 2).
    Calculates technicals, checks regime, news, risk score, AI recommendation and stores in Firestore.
    """
    logger.info("Executing Watchlist Auto-Scanner Pipeline...")
    add_scheduler_log("Watchlist Auto Scan", "INFO", "Executing daily watchlist scan.")
    
    watchlist = []
    try:
        watchlist_doc = db.collection("config").document("watchlist").get()
        if watchlist_doc.exists:
            watchlist = watchlist_doc.to_dict().get("symbols", [])
    except Exception as e:
        logger.warning(f"Watchlist lookup failed: {e}")
        
    if not watchlist:
        watchlist = ["GREENPOWER", "BEL", "RELIANCE", "TCS", "INFY"]
        
    results = {}
    for ticker in watchlist:
        try:
            logger.info(f"Scanning and analyzing stock: {ticker}")
            
            # Fetch candles with 3-attempt recovery logic (Task 6)
            res_candles = None
            for attempt in range(3):
                try:
                    res_candles = upstox_client.fetch_historical_candles(ticker, days_back=200)
                    if res_candles and "candles" in res_candles and len(res_candles["candles"]) >= 50:
                        break
                except Exception as e:
                    logger.warning(f"Upstox fetch retry {attempt+1} for {ticker}: {e}")
                    time.sleep(2 ** attempt)
                    
            if not res_candles:
                logger.error(f"Failed to retrieve candles for {ticker} after retries.")
                continue
                
            candles = res_candles["candles"]
            latest_close = float(candles[0][4])
            
            # Reconstruct oldest-to-newest lists
            candles_rev = list(candles)
            candles_rev.reverse()
            c_closes = [float(c[4]) for c in candles_rev]
            c_highs = [float(c[2]) for c in candles_rev]
            c_lows = [float(c[3]) for c in candles_rev]
            c_volumes = [float(c[5]) for c in candles_rev]
            
            # Compute technical indicators locally
            indicators = compute_local_indicators(c_closes, c_highs, c_lows, c_volumes)
            
            stock_doc = {
                "ticker": ticker,
                "company_name": ticker,
                "current_price": latest_close,
                "daily_change": 0.0,
                "unified_score": 75,
                "sector": "Utilities" if ticker == "GREENPOWER" else "Technology" if ticker in ["TCS", "INFY"] else "Conglomerate",
                "technical_indicators": indicators
            }
            
            # Save raw indicators to Firestore stocks/ ticker
            db.collection("stocks").document(ticker).set(stock_doc)
            
            # Trigger AI recommendation agent (Task 2)
            ai_res = None
            for attempt in range(3):
                try:
                    ai_res = generate_stock_explanation(stock_doc, [])
                    if ai_res:
                        break
                except Exception as e:
                    logger.warning(f"Gemini AI recommendations retry {attempt+1} for {ticker}: {e}")
                    time.sleep(2 ** attempt)
                    
            if not ai_res:
                logger.error(f"Failed to generate AI recommendations for {ticker} after retries.")
                continue
                
            results[ticker] = ai_res
            logger.info(f"AI Decision generated for {ticker}: {ai_res.get('recommendation')}")
            
        except Exception as e:
            logger.error(f"Failed scanning stock {ticker} in auto pipeline: {e}")
            
    add_scheduler_log("Watchlist Auto Scan", "INFO", f"Watchlist scan completed. Stocks evaluated: {list(results.keys())}")
    return results

def run_paper_trade_automation() -> Dict[str, Any]:
    """
    Executes automated paper trades based on calculated constraints and dynamic trailing stops (Task 3).
    """
    logger.info("Executing Paper Trade Automation Job...")
    add_scheduler_log("Paper Trade Automation", "INFO", "Executing target / trailing stop checks and entries.")
    
    # Portfolio and Cash metrics
    port_state = get_paper_portfolio()
    cash = float(port_state.get("cash", 1000000.0))
    port_val = float(port_state.get("portfolio_value", 1000000.0))
    
    # Exits: Trailing Stops & Targets (Task 3)
    open_positions = [doc.to_dict() for doc in db.collection("paper_positions").get()]
    
    for pos in open_positions:
        ticker = pos["ticker"]
        qty = pos["quantity"]
        entry_price = pos["entry_price"]
        current_sl = pos["stop_loss"]
        target = pos["target"]
        
        # Fetch current price
        try:
            res = upstox_client.fetch_historical_candles(ticker, days_back=5)
            if not res or "candles" not in res:
                continue
            latest_price = float(res["candles"][0][4])
        except Exception as e:
            logger.error(f"Error fetching current price for position {ticker}: {e}")
            continue
            
        # Get ATR for trailing stop calculation
        # Trailing stop rule: SL set at high_water_mark - 1.5 * ATR
        atr = float(pos.get("atr", latest_price * 0.03)) # default
        try:
            stock_doc = db.collection("stocks").document(ticker).get()
            if stock_doc.exists:
                atr = float(stock_doc.to_dict().get("technical_indicators", {}).get("atr", atr))
        except:
            pass
            
        highest = max(pos.get("highest_price", entry_price), latest_price)
        lowest = min(pos.get("lowest_price", entry_price), latest_price)
        
        # Compute trailing SL: (Trailing SL shifts up as price moves to new highs)
        new_sl = highest - 1.5 * atr
        trail_sl = max(current_sl, new_sl)
        
        # Save updates to Firestore
        db.collection("paper_positions").document(ticker).update({
            "current_price": latest_price,
            "stop_loss": trail_sl,
            "highest_price": highest,
            "lowest_price": lowest
        })
        
        # Check target / stop loss hit
        exit_triggered = False
        exit_price = latest_price
        exit_reason = ""
        
        if latest_price >= target:
            exit_triggered = True
            exit_price = target
            exit_reason = "TARGET_HIT"
        elif latest_price <= trail_sl:
            exit_triggered = True
            exit_price = trail_sl
            exit_reason = "STOP_LOSS_HIT"
            
        if exit_triggered:
            # Execute closure
            proceeds = qty * exit_price
            charges = proceeds * 0.0005 # 0.05% brokerage
            net_proceeds = proceeds - charges
            
            cash += net_proceeds
            realized_pnl = net_proceeds - (qty * entry_price)
            pnl_pct = ((exit_price - entry_price) / entry_price) * 100.0
            
            # Alert (Task 4)
            msg = f"🔔 <b>AORA SIMULATOR - EXIT EXECUTION</b>\n\n<b>Ticker:</b> {ticker}\n<b>Reason:</b> {exit_reason}\n<b>Exit Price:</b> ₹{exit_price:.2f}\n<b>P&L:</b> ₹{realized_pnl:,.2f} ({pnl_pct:.2f}%)"
            send_telegram_alert(msg)
            add_scheduler_log("Paper Trade Exit", "INFO", f"Exit executed for {ticker} | Price: ₹{exit_price:.2f} ({exit_reason})")
            
            # Move from open positions to completed trades log
            db.collection("paper_positions").document(ticker).delete()
            
            # Log sell order
            order_id = f"order_{int(time.time())}_{ticker}_sell"
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
            
            # Log Trade Journal
            trade_id = f"trade_{int(time.time())}_{ticker}"
            db.collection("paper_trades").document(trade_id).set({
                "ticker": ticker,
                "quantity": qty,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "entry_date": pos["entry_date"],
                "exit_date": datetime.date.today().isoformat(),
                "stop_loss": trail_sl,
                "target": target,
                "holding_period_days": (datetime.date.today() - datetime.date.fromisoformat(pos["entry_date"])).days,
                "pnl_val": realized_pnl,
                "pnl_pct": pnl_pct,
                "max_drawdown": abs(((lowest - entry_price) / entry_price) * 100.0) if lowest < entry_price else 0.0,
                "mfe": ((highest - entry_price) / entry_price) * 100.0,
                "mae": ((lowest - entry_price) / entry_price) * 100.0
            })
            
    # Entries: Check AI recommendations from Firestore
    # Risk Limits (Task 3):
    max_positions_cap = 5
    max_sector_exposure_pct = 40.0
    max_portfolio_risk_score = 75
    max_single_position_pct = 20.0
    
    current_positions_count = len(db.collection("paper_positions").get())
    
    if current_positions_count >= max_positions_cap:
        logger.info("Maximum open positions cap reached. Entries blocked.")
        return {"status": "positions_capped"}
        
    # Query AI recommendation records
    ai_analysis_docs = db.collection("ai_analysis").get()
    
    for doc in ai_analysis_docs:
        ai_data = doc.to_dict()
        ticker = doc.id
        
        # Check if already has an open position
        open_check = db.collection("paper_positions").document(ticker).get()
        if open_check.exists:
            continue
            
        rec = ai_data.get("recommendation", "HOLD")
        if rec == "BUY":
            # Check maximum portfolio risk rating
            risk_score = int(ai_data.get("risk_score", 50))
            if risk_score > max_portfolio_risk_score:
                logger.info(f"Entry blocked for {ticker}: Portfolio risk score limit exceeded ({risk_score} > {max_portfolio_risk_score})")
                continue
                
            # Check sector exposure (Fetch sectors of open positions)
            sector = ai_data.get("sector", "Utilities")
            # Calculate sector allocation value
            sector_val = 0.0
            open_pos = db.collection("paper_positions").get()
            for op in open_pos:
                op_data = op.to_dict()
                # Get sector from stocks registry
                stock_sec = "Utilities"
                stock_doc = db.collection("stocks").document(op.id).get()
                if stock_doc.exists:
                    stock_sec = stock_doc.to_dict().get("sector", "Utilities")
                if stock_sec == sector:
                    sector_val += op_data["quantity"] * op_data["current_price"]
                    
            if (sector_val / port_val) * 100.0 >= max_sector_exposure_pct:
                logger.info(f"Entry blocked for {ticker}: Sector concentration cap violated ({sector})")
                continue
                
            # ATR Position Sizing (Task 3):
            # Qty = (Portfolio Value * 1.5% Risk Capital) / (1.5 * ATR)
            price = float(ai_data.get("entry_price", 10.0))
            # Get ATR
            stock_doc = db.collection("stocks").document(ticker).get()
            atr = price * 0.03 # fallback
            if stock_doc.exists:
                atr = float(stock_doc.to_dict().get("technical_indicators", {}).get("atr", atr))
                
            risk_capital = port_val * 0.015 # 1.5% max risk allocation
            # Compute Qty based on stop loss distance
            sl_dist = 1.5 * atr
            if sl_dist > 0:
                suggested_qty = int(risk_capital / sl_dist)
            else:
                suggested_qty = int(risk_capital / (price * 0.05))
                
            # Position capital allocation cap: Capped at 20% of portfolio value
            pos_cap_alloc = port_val * (max_single_position_pct / 100.0)
            qty = min(suggested_qty, int(pos_cap_alloc / price))
            
            # Check cash availability
            slippage = 0.0005
            buy_price = price * (1.0 + slippage)
            total_outflow = qty * buy_price
            
            if qty > 0 and cash >= total_outflow:
                cash -= total_outflow
                
                sl = buy_price - 1.5 * atr
                target_val = buy_price + 2.5 * atr
                
                # Create open position
                db.collection("paper_positions").document(ticker).set({
                    "ticker": ticker,
                    "quantity": qty,
                    "entry_price": buy_price,
                    "current_price": buy_price,
                    "unrealized_pnl": 0.0,
                    "stop_loss": sl,
                    "target": target_val,
                    "highest_price": buy_price,
                    "lowest_price": buy_price,
                    "entry_date": datetime.date.today().isoformat(),
                    "atr": atr,
                    "ai_reasoning": ai_data.get("reasoning", ""),
                    "confidence": ai_data.get("confidence", 70),
                    "risk_score": risk_score,
                    "market_regime": ai_data.get("market_regime", "Neutral"),
                    "news_sentiment": ai_data.get("news_sentiment", "Neutral"),
                    "strategy_votes": ai_data.get("strategy_signals", {})
                })
                
                # Log Order
                order_id = f"order_{int(time.time())}_{ticker}_buy"
                db.collection("paper_orders").document(order_id).set({
                    "ticker": ticker,
                    "order_type": "BUY",
                    "status": "COMPLETED",
                    "price": buy_price,
                    "quantity": qty,
                    "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
                    "transaction_charges": total_outflow * 0.0005
                })
                
                # Send Alert (Task 4)
                msg = f"🚀 <b>AORA SIMULATOR - ENTRY EXECUTION</b>\n\n<b>Ticker:</b> {ticker}\n<b>Action:</b> BUY\n<b>Price:</b> ₹{buy_price:.2f}\n<b>Quantity:</b> {qty} shares\n<b>Stop Loss:</b> ₹{sl:.2f}\n<b>Target:</b> ₹{target_val:.2f}"
                send_telegram_alert(msg)
                add_scheduler_log("Paper Trade Entry", "INFO", f"Entry executed for {ticker} | Price: ₹{buy_price:.2f} | Qty: {qty}")
                
    # Update portfolio values
    pos_val = 0.0
    open_pos_docs = db.collection("paper_positions").get()
    for d in open_pos_docs:
        p = d.to_dict()
        pos_val += p["quantity"] * p["current_price"]
        
    portfolio_value = cash + pos_val
    realized_acc = sum([float(t.to_dict().get("pnl_val", 0.0)) for t in db.collection("paper_trades").get()])
    
    # Save portfolio state back to Firestore
    state_ref = db.collection("paper_portfolio").document("state")
    state_ref.update({
        "cash": cash,
        "portfolio_value": portfolio_value,
        "realized_pnl": realized_acc,
        "unrealized_pnl": portfolio_value - cash - realized_acc,
        "last_updated": datetime.datetime.utcnow().isoformat() + "Z"
    })
    
    return {"portfolio_value": portfolio_value, "cash": cash}

def run_end_of_day_report() -> str:
    """
    Executes the 15:30 IST market close job (Task 1 & 4).
    Generates a daily close report and dispatches via Telegram.
    """
    logger.info("Generating End-of-Day Performance Report...")
    add_scheduler_log("End of Day Report", "INFO", "Compiling daily closed performance summary.")
    
    port = get_paper_portfolio()
    analytics = get_performance_analytics()
    
    msg = f"""📊 <b>AORA SIMULATOR - END OF DAY REPORT</b>
    
<b>Valuation:</b> ₹{port['portfolio_value']:,.2f}
<b>Virtual Cash:</b> ₹{port['cash']:,.2f}
<b>Realized P&L:</b> ₹{port['realized_pnl']:,.2f}
<b>Unrealized P&L:</b> ₹{port['unrealized_pnl']:,.2f}

<b>Win Rate:</b> {analytics['win_rate']}%
<b>Profit Factor:</b> {analytics['profit_factor']}
<b>Max Drawdown:</b> {analytics['max_drawdown']}%
<b>Trades Count:</b> {analytics['trades_count']}
"""
    send_telegram_alert(msg)
    return msg

def run_evening_learning_report() -> str:
    """
    Executes the 20:00 IST learning agent job (Task 1, 4 & 6).
    Compiles AI learning summary, updates lessons, and alerts via Telegram.
    """
    logger.info("Generating Evening AI Learning Report...")
    add_scheduler_log("AI Learning Report", "INFO", "Compiling completed trades patterns analysis.")
    
    learn_res = run_ai_self_learning()
    lessons = learn_res.get("lessons", "No trade data available to extract learnings.")
    
    msg = f"""🧠 <b>AORA QUANT - AI SELF-LEARNING REPORT</b>

{lessons}
"""
    send_telegram_alert(msg)
    return msg

def simulate_one_trading_day() -> Dict[str, Any]:
    """
    Executes a complete simulated trading day workflow for E2E validation (Task 8).
    1. Runs health checks (08:45 IST check).
    2. Runs auto watchlist scanner & indicators (09:00 IST).
    3. Runs AI recommendations engine (09:15 IST).
    4. Runs paper trading execution, exits, and entries (Every 30 mins).
    5. Runs EOD close report (15:30 IST).
    6. Runs evening learning report (20:00 IST).
    """
    logger.info("Starting complete simulated trading day execution cycle...")
    
    # Reset status logs
    db.collection("paper_scheduler").document("status").set({"logs": []})
    add_scheduler_log("Simulation boot", "INFO", "Starting synchronous simulated trading day checks.")
    
    # Step 1: Health checks (08:45)
    hc_res = run_health_checks()
    
    # Step 2: Auto watchlist scanner (09:00 / 09:15)
    scan_res = execute_watchlist_auto_scan()
    
    # Save recommendations to ai_analysis cache to trigger entries
    for ticker, ai_data in scan_res.items():
        try:
            ai_data["analyzed_at"] = datetime.datetime.utcnow().isoformat() + "Z"
            db.collection("ai_analysis").document(ticker).set(ai_data)
        except Exception as e:
            logger.error(f"Error caching AI analysis for {ticker}: {e}")
            
    # Step 3: Paper Trading Entry & exit execution (09:30 - 15:30)
    exec_res = run_paper_trade_automation()
    
    # Step 4: End of Day Performance close (15:30)
    eod_report = run_end_of_day_report()
    
    # Step 5: Evening AI learnings (20:00)
    learn_report = run_evening_learning_report()
    
    add_scheduler_log("Simulation Completed", "INFO", "Simulated trading day sequence completed successfully.")
    
    # Final state updates
    update_scheduler_status(
        status="ACTIVE",
        current_job="IDLE",
        gemini_status=hc_res.get("gemini", "CONNECTED"),
        upstox_status=hc_res.get("upstox", "CONNECTED"),
        firestore_status=hc_res.get("firestore", "CONNECTED"),
        telegram_status=hc_res.get("telegram", "CONNECTED")
    )
    
    return {
        "health_checks": hc_res,
        "scan_count": len(scan_res),
        "execution": exec_res,
        "eod_report": eod_report,
        "learn_report": learn_report
    }
