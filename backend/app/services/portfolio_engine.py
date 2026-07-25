import logging
import time
import httpx
import pytz
from datetime import datetime, time as dt_time
from typing import Dict, Any, List
from app.db import db
from app.data_sources.market_data import upstox_client
from app.agents.explanation import get_live_portfolio_data
from app.services.capital_allocation import calculate_portfolio_quality_score, generate_rebalance_suggestions

logger = logging.getLogger(__name__)

IST = pytz.timezone('Asia/Kolkata')

def is_market_open_ist() -> bool:
    """Verifies if the Indian stock market is currently open (Mon-Fri 09:15 - 15:30 IST)."""
    now_ist = datetime.now(IST)
    if now_ist.weekday() >= 5: # Saturday or Sunday
        return False
        
    start = dt_time(9, 15)
    end = dt_time(15, 30)
    return start <= now_ist.time() <= end

def verify_connectivity() -> bool:
    """Checks internet connectivity to verify outbound request routing."""
    try:
        res = httpx.get("https://www.google.com", timeout=3.0)
        return res.status_code == 200
    except Exception:
        return False

def verify_upstox_session() -> bool:
    """Checks if the Upstox session token is valid and active."""
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

async def get_portfolio_summary() -> Dict[str, Any]:
    """Retrieves full portfolio state including balances, holdings, quality score, and suggestions."""
    portfolio = get_live_portfolio_data()
    
    # Calculate sector exposure
    holdings = portfolio.get("holdings", [])
    cash = float(portfolio.get("cash_available", 0.0))
    
    holdings_value = 0.0
    sector_values = {}
    for h in holdings:
        qty = float(h.get("quantity", 0))
        avg_cost = float(h.get("average_price", h.get("entryPrice", 0.0)))
        current_price = float(h.get("last_price", h.get("close", avg_cost)))
        
        pos_val = qty * current_price
        holdings_value += pos_val
        
        sector = h.get("sector", "Other")
        sector_values[sector] = sector_values.get(sector, 0.0) + pos_val
        
    portfolio_value = cash + holdings_value
    
    sector_exposures = {}
    if portfolio_value > 0:
        for sec, val in sector_values.items():
            sector_exposures[sec] = round((val / portfolio_value) * 100.0, 2)
            
    # Compute quality score
    health_mock = {
        "portfolio_volatility": 15.0,
        "sector_exposures": sector_exposures
    }
    
    quality_score = calculate_portfolio_quality_score(portfolio, health_mock)
    rebalance_suggestions = generate_rebalance_suggestions(portfolio, health_mock)
    
    return {
        "portfolio_value": round(portfolio_value, 2),
        "holdings_value": round(holdings_value, 2),
        "cash_available": round(cash, 2),
        "unrealized_pnl": round(portfolio.get("unrealized_pnl", 0.0), 2),
        "realized_pnl": round(portfolio.get("realized_pnl", 0.0), 2),
        "sector_exposures": sector_exposures,
        "quality_score": round(quality_score, 1),
        "rebalance_suggestions": rebalance_suggestions,
        "authenticated": portfolio.get("authenticated", False)
    }

async def validate_trade_constraints(
    ticker: str,
    quantity: int,
    price: float,
    transaction_type: str
) -> List[str]:
    """
    Enforces compliance and safety policies before executing a trade.
    Checks market status, connectivity, session auth, cash balance, exposure caps, and duplicates.
    """
    violations = []
    
    # 1. Market Status
    if not is_market_open_ist():
        violations.append("Market is closed. Real trading is only permitted between 09:15 and 15:30 IST.")
        
    # 2. Connectivity Check
    if not verify_connectivity():
        violations.append("Network check failed. Outbound internet connection is unavailable.")
        
    # 3. Auth Session Verification
    if not verify_upstox_session():
        violations.append("Upstox session authentication has expired. Please log in again.")
        
    # 4. Duplicate Check (within the last 5 minutes)
    try:
        five_mins_ago = time.time() - 300
        recent_orders = db.collection("order_logs") \
                          .where("ticker", "==", ticker.upper()) \
                          .where("side", "==", transaction_type.upper()) \
                          .get()
        for doc in recent_orders:
            o_data = doc.to_dict()
            o_time = o_data.get("timestamp", 0)
            if o_time > five_mins_ago and o_data.get("execution_status") in ["SUCCESS", "PENDING_APPROVAL"]:
                violations.append(f"Duplicate order detected for {ticker} within the last 5 minutes.")
                break
    except Exception as e:
        logger.warning(f"Error checking duplicate order attempts: {e}")
        
    # 5. Position Exposure & Balance Bounds
    portfolio = get_live_portfolio_data()
    cash = float(portfolio.get("cash_available", 0.0))
    order_value = quantity * price
    
    if transaction_type.upper() == "BUY" and order_value > cash:
        violations.append(f"Insufficient funds. Order Value: ₹{order_value:,.2f} | Available Margin: ₹{cash:,.2f}")
        
    # Concentration Limit (20% cap per stock)
    holdings = portfolio.get("holdings", [])
    holdings_value = 0.0
    target_ticker_value = 0.0
    
    for h in holdings:
        h_ticker = h.get("ticker", h.get("tradingsymbol", "")).upper()
        h_qty = float(h.get("quantity", h.get("qty", 0.0)))
        h_price = float(h.get("last_price", h.get("current_price", 0.0)))
        h_val = h_qty * h_price
        holdings_value += h_val
        if h_ticker == ticker.upper():
            target_ticker_value = h_val
            
    portfolio_value = cash + holdings_value
    if portfolio_value > 0 and transaction_type.upper() == "BUY":
        new_exposure_pct = ((target_ticker_value + order_value) / portfolio_value) * 100.0
        if new_exposure_pct > 20.0:
            violations.append(f"Position size violation. Allocation in {ticker} would exceed single-stock cap (20%). Proposed: {new_exposure_pct:.1f}%")
            
    return violations
