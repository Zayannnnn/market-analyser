import logging
import time
import httpx
from datetime import datetime, time as dt_time
import pytz
from typing import Dict, Any, List, Optional
from app.db import db
from app.config import settings
from app.data_sources.market_data import upstox_client
from app.services.market_regime import determine_market_regime
from app.agents.explanation import get_live_portfolio_data
from app.services.instrument_lookup import get_upstox_instrument

logger = logging.getLogger(__name__)

# Timezone configuration for IST
IST = pytz.timezone('Asia/Kolkata')

def is_indian_market_open() -> bool:
    """Verifies if the Indian market is open (Mon-Fri 09:15 - 15:30 IST)."""
    now_ist = datetime.now(IST)
    if now_ist.weekday() >= 5: # Saturday or Sunday
        return False
        
    start_time = dt_time(9, 15)
    end_time = dt_time(15, 30)
    return start_time <= now_ist.time() <= end_time

def check_internet_connection() -> bool:
    """Verifies internet connectivity by requesting google.com."""
    try:
        res = httpx.get("https://www.google.com", timeout=3.0)
        return res.status_code == 200
    except Exception:
        return False

def check_upstox_authentication() -> bool:
    """Verifies if Upstox token is valid by hitting users profile endpoint."""
    token = upstox_client.get_access_token()
    if not token:
        return False
    try:
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }
        res = httpx.get("https://api.upstox.com/v2/user/profile", headers=headers, timeout=5.0)
        return res.status_code == 200
    except Exception:
        return False

def get_live_execution_mode() -> str:
    """Retrieves current execution mode (OFF, CONFIRM, AUTO) from Firestore."""
    try:
        doc = db.collection("live_trading").document("config").get()
        if doc.exists:
            return doc.to_dict().get("mode", "CONFIRM")
    except Exception:
        pass
    return "CONFIRM"

def set_live_execution_mode(mode: str):
    """Sets live execution mode in Firestore."""
    if mode not in ["OFF", "CONFIRM", "AUTO"]:
        raise ValueError("Invalid execution mode. Choose OFF, CONFIRM, or AUTO.")
    db.collection("live_trading").document("config").set({
        "mode": mode,
        "updated_at": datetime.utcnow().isoformat() + "Z"
    }, merge=True)

def is_live_trading_enabled() -> bool:
    """Checks if live trading is enabled (default: False for security)."""
    try:
        doc = db.collection("live_trading").document("config").get()
        if doc.exists:
            return doc.to_dict().get("live_trading_enabled", False)
    except Exception:
        pass
    return False

def check_execution_safety(
    ticker: str,
    qty: int,
    price: float,
    transaction_type: str,
    portfolio: Dict[str, Any]
) -> List[str]:
    """
    Safety Layer (Task 3).
    Verifies market open, internet, auth, exposure limits, and duplicate orders.
    Returns list of safety violations (empty if safe).
    """
    violations = []
    
    # 1. Market Open
    if not is_indian_market_open():
        violations.append("Market is closed. Live trading only permitted 09:15 - 15:30 IST.")
        
    # 2. Internet check
    if not check_internet_connection():
        violations.append("Internet connectivity check failed.")
        
    # 3. Auth check
    if not check_upstox_authentication() or not portfolio.get("authenticated", True):
        violations.append("Upstox API Authentication token is invalid or expired (401).")
        
    # 4. Duplicate order check (Placed in last 5 minutes)
    try:
        five_mins_ago = datetime.utcnow().timestamp() - 300
        recent_orders = db.collection("live_orders") \
                          .where("ticker", "==", ticker) \
                          .where("transaction_type", "==", transaction_type) \
                          .get()
        for doc in recent_orders:
            o_data = doc.to_dict()
            o_time = o_data.get("created_timestamp", 0)
            if o_time > five_mins_ago and o_data.get("status") in ["FILLED", "PENDING_APPROVAL"]:
                violations.append(f"Duplicate order detected for {ticker} within the last 5 minutes.")
                break
    except Exception as e:
        logger.warning(f"Error checking duplicate orders: {e}")
        
    # 5. Risk limits checks from Risk Engine (configurable Rules)
    try:
        from app.services.risk_engine import validate_portfolio_risk_rules
        risk_violations = validate_portfolio_risk_rules(ticker, qty, price, transaction_type, portfolio)
        violations.extend(risk_violations)
    except Exception as e:
        logger.error(f"Error calling validate_portfolio_risk_rules: {e}")
        violations.append(f"Risk Engine safety validation error: {e}")
        
    return violations

def send_telegram_order_alert(order_data: Dict[str, Any]):
    """Sends Telegram message with Action status and confirmation links."""
    bot_token = settings.telegram_bot_token
    chat_id = settings.telegram_chat_id
    if not bot_token or not chat_id:
        return
        
    ticker = order_data["ticker"]
    qty = order_data["quantity"]
    price = order_data["price"]
    tx_type = order_data["transaction_type"]
    status = order_data["status"]
    order_id = order_data["order_id"]
    reason = order_data.get("reason", "N/A")
    
    emoji = "📥 BUY" if tx_type == "BUY" else "📤 SELL"
    
    text = f"""
<b>🚨 Live Order Notification</b>
Action: <b>{emoji} {ticker}</b>
Quantity: <b>{qty} shares</b>
Price: <b>₹{price:,.2f}</b>
Status: <b>{status}</b>
Reason: <i>{reason}</i>
Time: <b>{datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S')}</b>
"""
    
    # Inline Confirmation Links (Task 6)
    if status == "PENDING_APPROVAL":
        # Base url
        backend_url = "https://market-analyser-backend-527531325658.us-central1.run.app"
        approve_url = f"{backend_url}/api/live/approve?order_id={order_id}"
        reject_url = f"{backend_url}/api/live/reject?order_id={order_id}"
        
        text += f"""
<i>Manual Approval Mode (CONFIRM) Active. Confirm execution:</i>
👉 <a href="{approve_url}">Approve Order</a>
👉 <a href="{reject_url}">Reject Order</a>
"""

    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        httpx.post(url, json=payload, timeout=5.0)
    except Exception as e:
        logger.warning(f"Failed to send Telegram live alert: {e}")

def place_live_order(
    ticker: str,
    qty: int,
    price: float,
    order_type: str,         # "LIMIT" | "MARKET"
    transaction_type: str,   # "BUY" | "SELL"
    reason: str = "",
    confidence: int = 70,
    risk_score: int = 50,
    regime: str = "Neutral"
) -> Dict[str, Any]:
    """
    Live Order Placement workflow (Task 2 & 3 & 4 & 5).
    """
    start_time = time.time()
    order_id = f"live_order_{int(time.time() * 1000)}"
    mode = get_live_execution_mode()
    
    order_doc = {
        "order_id": order_id,
        "ticker": ticker,
        "quantity": qty,
        "price": price,
        "order_type": order_type,
        "transaction_type": transaction_type,
        "reason": reason,
        "confidence": confidence,
        "risk_score": risk_score,
        "market_regime": regime,
        "mode": mode,
        "created_timestamp": time.time(),
        "created_at": datetime.utcnow().isoformat() + "Z",
        "status": "OFFLINE" if mode == "OFF" else "PENDING_APPROVAL" if mode == "CONFIRM" else "PENDING_SAFETY",
        "broker_response": "Mode OFF prevents execution." if mode == "OFF" else "Pending manual approval." if mode == "CONFIRM" else "",
        "execution_latency_ms": 0
    }
    
    db.collection("live_orders").document(order_id).set(order_doc)
    
    if mode == "OFF":
        send_telegram_order_alert(order_doc)
        return order_doc
        
    if mode == "CONFIRM":
        # Send inline telegram options
        send_telegram_order_alert(order_doc)
        return order_doc
        
    # If AUTO, run E2E Execution immediately
    return execute_safety_and_submit_order(order_id, start_time)

def execute_safety_and_submit_order(order_id: str, start_time: float) -> Dict[str, Any]:
    """Validates safety limits and places order with Upstox if enabled."""
    doc_ref = db.collection("live_orders").document(order_id)
    order_data = doc_ref.get().to_dict()
    
    ticker = order_data["ticker"]
    qty = order_data["quantity"]
    price = order_data["price"]
    tx_type = order_data["transaction_type"]
    order_type = order_data["order_type"]
    
    portfolio = get_live_portfolio_data()
    violations = check_execution_safety(ticker, qty, price, tx_type, portfolio)
    
    if violations:
        msg = f"Safety violations: {', '.join(violations)}"
        logger.warning(msg)
        order_data.update({
            "status": "REJECTED_SAFETY",
            "broker_response": msg,
            "execution_latency_ms": int((time.time() - start_time) * 1000)
        })
        doc_ref.set(order_data)
        send_telegram_order_alert(order_data)
        return order_data
        
    # Check if live cash trading is enabled (default: False for security)
    if is_live_trading_enabled():
        try:
            token = upstox_client.get_access_token()
            inst = get_upstox_instrument(ticker)
            if not inst:
                raise ValueError(f"Upstox instrument key lookup failed for {ticker}")
                
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            body = {
                "quantity": int(qty),
                "product": "D", # Delivery Mode
                "validity": "DAY",
                "price": float(price),
                "tag": "AORA",
                "instrument_token": inst["instrument_key"],
                "order_type": order_type,
                "transaction_type": tx_type,
                "disclosed_quantity": 0,
                "trigger_price": 0.0,
                "is_amo": False
            }
            
            res = httpx.post("https://api.upstox.com/v2/order/place", json=body, headers=headers, timeout=10.0)
            payload = res.json()
            latency = int((time.time() - start_time) * 1000)
            
            if res.status_code == 200 and payload.get("status") == "success":
                order_data.update({
                    "status": "FILLED",
                    "broker_response": f"Upstox Order ID: {payload.get('data', {}).get('order_id')}",
                    "execution_latency_ms": latency
                })
            else:
                order_data.update({
                    "status": "REJECTED_BROKER",
                    "broker_response": f"Upstox Code {res.status_code}: {res.text}",
                    "execution_latency_ms": latency
                })
        except Exception as e:
            latency = int((time.time() - start_time) * 1000)
            order_data.update({
                "status": "REJECTED_BROKER",
                "broker_response": f"Internal exception occurred: {e}",
                "execution_latency_ms": latency
            })
    else:
        # SIMULATED FILLED (Safe Mode - defaults)
        latency = int((time.time() - start_time) * 1000)
        order_data.update({
            "status": "FILLED_SIMULATED",
            "broker_response": "Simulated filled. Live trading remains disabled by default for security.",
            "execution_latency_ms": latency
        })
        
    doc_ref.set(order_data)
    send_telegram_order_alert(order_data)
    return order_data

def approve_live_order(order_id: str) -> bool:
    """Manually approves and triggers a pending order (Task 6)."""
    doc_ref = db.collection("live_orders").document(order_id)
    doc = doc_ref.get()
    if not doc.exists:
        return False
        
    order_data = doc.to_dict()
    if order_data.get("status") != "PENDING_APPROVAL":
        return False
        
    # Update state to pending safety
    order_data["status"] = "PENDING_SAFETY"
    doc_ref.set(order_data)
    
    # Trigger execution
    execute_safety_and_submit_order(order_id, order_data["created_timestamp"])
    return True

def reject_live_order(order_id: str) -> bool:
    """Manually rejects and cancels a pending order (Task 6)."""
    doc_ref = db.collection("live_orders").document(order_id)
    doc = doc_ref.get()
    if not doc.exists:
        return False
        
    order_data = doc.to_dict()
    if order_data.get("status") != "PENDING_APPROVAL":
        return False
        
    order_data.update({
        "status": "REJECTED_MANUAL",
        "broker_response": "Rejected manually by user response."
    })
    doc_ref.set(order_data)
    send_telegram_order_alert(order_data)
    return True

def run_live_auto_trading():
    """
    Continuous live execution scanner.
    Checks top scored opportunities from Shariah watchlist. If they hit buy criteria (>75 score)
    and aren't already held, prepares the order, validates safety bounds, and routes or requests approval.
    """
    mode = get_live_execution_mode()
    if mode == "OFF":
        logger.info("Live auto trading skipped: Mode is OFF.")
        return
        
    logger.info(f"Running background Live Auto Trading scanner (Mode: {mode})")
    
    # 1. Fetch live portfolio
    portfolio = get_live_portfolio_data()
    if not portfolio.get("authenticated", False):
        logger.warning("Auto trading scanner: portfolio is not authenticated.")
        return
        
    cash = float(portfolio.get("cash_available", 0.0))
    
    # 2. Scan Shariah Watchlist from Firestore
    try:
        from app.services.risk_engine import get_risk_rules
        watchlist_docs = db.collection("halal_watchlist").get()
        for doc in watchlist_docs:
            w_data = doc.to_dict()
            ticker = w_data["ticker"].upper()
            
            # Check if already held
            is_held = any(h.get("ticker", h.get("tradingsymbol", "")).upper() == ticker for h in portfolio.get("holdings", []))
            if is_held:
                continue
                
            # Fetch AI score
            ai_doc = db.collection("ai_analysis").document(ticker).get()
            if not ai_doc.exists:
                continue
                
            ai_data = ai_doc.to_dict()
            score = ai_data.get("unified_score", 0)
            rec = ai_data.get("recommendation", "HOLD")
            
            # Criteria: BUY recommendation and score > 75
            if rec == "BUY" and score > 75:
                logger.info(f"Found opportunity for {ticker} (Score: {score}). Validating safety...")
                
                # Fetch price
                from app.data_sources.market_data import get_market_data
                try:
                    price = float(ai_data.get("entry_price", get_market_data(ticker).get("price", 0.0)))
                except:
                    continue
                atr = float(ai_data.get("atr", price * 0.03))
                
                # 1.5% max risk capital sizing
                total_portfolio_value = cash + sum(float(h.get("quantity", 0)) * float(h.get("last_price", 0.0)) for h in portfolio.get("holdings", []))
                risk_capital = total_portfolio_value * 0.015
                sl_dist = 2 * atr
                suggested_qty = int(risk_capital / sl_dist) if sl_dist > 0 else int(risk_capital / (price * 0.05))
                
                # Cap single stock exposure to dynamic rule (default 20%)
                rules = get_risk_rules()
                max_stock_pct = float(rules.get("max_single_stock_exposure_pct", 20.0)) / 100.0
                max_alloc = total_portfolio_value * max_stock_pct
                qty = min(suggested_qty, int(max_alloc / price))
                
                if qty <= 0:
                    continue
                    
                # Place the order through safety layer
                logger.info(f"Submitting live auto order for {ticker}: {qty} shares @ ₹{price}")
                place_live_order(
                    ticker=ticker,
                    qty=qty,
                    price=price,
                    order_type="LIMIT",
                    transaction_type="BUY",
                    reason=f"Auto-generated from Watchlist scanner with AI Score {score}/100",
                    confidence=score,
                    risk_score=ai_data.get("risk_score", 50),
                    regime=ai_data.get("market_regime", "Neutral")
                )
    except Exception as e:
        logger.error(f"Error in run_live_auto_trading loop: {e}", exc_info=True)

def monitor_live_positions():
    """
    Checks active holdings positions against dynamic Stop-Loss and Profit targets.
    If a trigger is hit:
    - If mode is AUTO, submits a market sell order immediately to protect capital.
    - If mode is CONFIRM or OFF, dispatches a Telegram alert.
    """
    mode = get_live_execution_mode()
    logger.info(f"Running background Live Position Monitor (Mode: {mode})")
    
    portfolio = get_live_portfolio_data()
    if not portfolio.get("authenticated", False):
        return
        
    holdings = portfolio.get("holdings", [])
    
    try:
        from app.services.risk_engine import get_risk_rules
        rules = get_risk_rules()
        
        # Load stop loss / take profit rules (percentages)
        sl_pct = float(rules.get("stop_loss_pct", 10.0)) / 100.0
        tp_pct = float(rules.get("target_profit_pct", 25.0)) / 100.0
        
        for h in holdings:
            ticker = h.get("ticker", h.get("tradingsymbol", "Unknown")).upper()
            qty = int(float(h.get("quantity", h.get("qty", 0.0))))
            avg_cost = float(h.get("average_price", 0.0))
            current_price = float(h.get("last_price", h.get("current_price", 0.0)))
            
            if qty <= 0 or avg_cost <= 0:
                continue
                
            pnl_pct = (current_price - avg_cost) / avg_cost
            
            trigger_hit = False
            reason = ""
            
            if pnl_pct <= -sl_pct:
                trigger_hit = True
                reason = f"STOP_LOSS_TRIGGERED (PnL: {pnl_pct*100:.2f}% <= -{sl_pct*100:.1f}%)"
            elif pnl_pct >= tp_pct:
                trigger_hit = True
                reason = f"TAKE_PROFIT_TRIGGERED (PnL: {pnl_pct*100:.2f}% >= {tp_pct*100:.1f}%)"
                
            if trigger_hit:
                logger.warning(f"Position Alert for {ticker}: {reason}")
                if mode == "AUTO":
                    logger.info(f"Auto mode active. Exiting position {ticker} immediately.")
                    place_live_order(
                        ticker=ticker,
                        qty=qty,
                        price=current_price,
                        order_type="MARKET",
                        transaction_type="SELL",
                        reason=f"Automated Exit: {reason}",
                        confidence=95,
                        risk_score=80,
                        regime="EOD"
                    )
                else:
                    # Send warning Telegram alert
                    bot_token = settings.telegram_bot_token
                    chat_id = settings.telegram_chat_id
                    if bot_token and chat_id:
                        text = f"🚨 <b>PORTFOLIO EXPOSURE ALERT</b>\n\nAsset <b>{ticker}</b> reached trigger bounds!\nAction: <b>SELL recommended</b>\nReason: <i>{reason}</i>\nCurrent Price: ₹{current_price:,.2f} (Entry: ₹{avg_cost:,.2f})\n\nMode is set to {mode}. Click Trade Panel to execute."
                        try:
                            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                            payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
                            httpx.post(url, json=payload, timeout=5.0)
                        except Exception as err:
                            logger.warning(f"Failed to dispatch monitoring alert: {err}")
    except Exception as e:
        logger.error(f"Error in monitor_live_positions loop: {e}", exc_info=True)

