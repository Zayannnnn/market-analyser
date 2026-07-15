import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

def calculate_portfolio_risk(
    portfolio: Dict[str, Any], 
    target_ticker: str, 
    target_price: float, 
    target_atr: float, 
    target_support: float
) -> Dict[str, Any]:
    """
    Dedicated Institutional Risk Engine.
    Calculates portfolio and position-level risk metrics, exposure limits, 
    and ATR-based position sizing for a target ticker.
    """
    holdings = portfolio.get("holdings", [])
    cash = float(portfolio.get("cash_available", 100000.0))
    realized_pnl = float(portfolio.get("realized_pnl", 0.0))
    unrealized_pnl = float(portfolio.get("unrealized_pnl", 0.0))
    
    # 1. Calculate Portfolio Value
    holdings_value = 0.0
    sector_values = {}
    position_values = {}
    
    target_holding_qty = 0.0
    target_holding_avg_cost = 0.0
    
    for h in holdings:
        qty = float(h.get("quantity", 0))
        # average price could be from Upstox (average_price) or frontend (entryPrice)
        avg_cost = float(h.get("average_price", h.get("entryPrice", 0.0)))
        trading_symbol = h.get("trading_symbol", h.get("ticker", "")).upper()
        
        # Estimate current price (fallback to average cost if not available)
        current_price = float(h.get("last_price", h.get("close", avg_cost)))
        
        pos_val = qty * current_price
        holdings_value += pos_val
        position_values[trading_symbol] = pos_val
        
        if trading_symbol == target_ticker.upper():
            target_holding_qty = qty
            target_holding_avg_cost = avg_cost
            
        # Group by Sector if sector key is available
        sector = h.get("sector", "Other")
        sector_values[sector] = sector_values.get(sector, 0.0) + pos_val
        
    total_portfolio_value = cash + holdings_value
    if total_portfolio_value <= 0:
        total_portfolio_value = 100000.0  # Safe fallback
        
    # 2. Sector & Cash Exposures
    sector_exposure = {}
    for sector, val in sector_values.items():
        sector_exposure[sector] = round((val / total_portfolio_value) * 100, 2)
        
    cash_exposure_pct = round((cash / total_portfolio_value) * 100, 2)
    
    # 3. Target Position Exposure & Risk
    target_position_value = target_holding_qty * target_price
    target_position_exposure = round((target_position_value / total_portfolio_value) * 100, 2)
    
    # 4. ATR Position Sizing (Institutional Standard)
    # Risk exactly 1.5% of total portfolio capital per trade
    risk_percent = 0.015
    capital_at_risk = total_portfolio_value * risk_percent
    
    # Stop loss distance defined as 2 * ATR
    stop_loss_distance = 2 * target_atr if target_atr > 0 else (target_price * 0.05)
    
    suggested_qty = 0
    suggested_allocation = 0.0
    if stop_loss_distance > 0:
        suggested_qty = int(capital_at_risk / stop_loss_distance)
        suggested_allocation = suggested_qty * target_price
        
    # Cap single position capital allocation at 20% of total portfolio value
    max_position_allocation = total_portfolio_value * 0.20
    if suggested_allocation > max_position_allocation:
        suggested_allocation = max_position_allocation
        suggested_qty = int(suggested_allocation / target_price) if target_price > 0 else 0

    # 5. Drawdown Risk (If asset drops to support level)
    support_drawdown = 0.0
    if target_holding_qty > 0 and target_support > 0 and target_support < target_price:
        support_drawdown = (target_price - target_support) * target_holding_qty
        
    max_drawdown_risk_pct = round((support_drawdown / total_portfolio_value) * 100, 2)
    
    # 6. Expected portfolio impact & Risk contribution (Task 3)
    # Estimate stock beta and volatility (defaults if not calculated)
    stock_beta = 1.1 
    stock_vol = 22.0
    
    risk_contribution = round((suggested_allocation * stock_vol) / total_portfolio_value, 2)
    
    # Estimate weighted beta impact
    new_beta = round(1.0 + (stock_beta - 1.0) * (suggested_allocation / total_portfolio_value), 2)
    expected_portfolio_impact = f"Allocation of {suggested_qty} shares would represent a {round((suggested_allocation/total_portfolio_value)*100, 1)}% exposure, projecting a target portfolio beta of {new_beta}."
    
    # 7. Aggregate Risk Score (10 to 100)
    # Concentrated positions, low cash, high drawdown risk, or high sector exposure increase the risk score
    base_risk = 30.0
    
    # Concentration penalty
    max_pos_exposure = max(position_values.values()) / total_portfolio_value if position_values else 0.0
    if max_pos_exposure > 0.25:
        base_risk += 15.0
        
    # Cash exposure reward
    if cash_exposure_pct > 50.0:
        base_risk -= 10.0
    elif cash_exposure_pct < 10.0:
        base_risk += 10.0
        
    # Sector exposure penalty
    max_sec_exposure = max(sector_exposure.values()) / 100.0 if sector_exposure else 0.0
    if max_sec_exposure > 0.40:
        base_risk += 15.0
        
    # Volatility / ATR adjustment
    atr_pct = (target_atr / target_price) * 100 if target_price > 0 else 0.0
    if atr_pct > 5.0:
        base_risk += 10.0
        
    risk_score = int(min(100, max(10, base_risk)))
    
    return {
        "portfolio_value": round(total_portfolio_value, 2),
        "holdings_value": round(holdings_value, 2),
        "cash_available": round(cash, 2),
        "cash_exposure_pct": cash_exposure_pct,
        "sector_exposure": sector_exposure,
        "position_value": round(target_position_value, 2),
        "position_exposure_pct": target_position_exposure,
        "atr_position_size": suggested_qty,
        "suggested_qty": suggested_qty,
        "suggested_allocation": round(suggested_allocation, 2),
        "max_drawdown_risk_pct": max_drawdown_risk_pct,
        "risk_score": risk_score,
        "realized_pnl": realized_pnl,
        "unrealized_pnl": unrealized_pnl,
        "target_holding_qty": target_holding_qty,
        "target_holding_avg_cost": target_holding_avg_cost,
        "risk_contribution_pct": risk_contribution,
        "expected_portfolio_impact": expected_portfolio_impact
    }
