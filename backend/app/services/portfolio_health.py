import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, List
from app.db import db
from app.data_sources.market_data import upstox_client
from app.services.technical_indicators import compute_local_indicators

logger = logging.getLogger(__name__)

def calculate_portfolio_health_metrics(portfolio: Dict[str, Any]) -> Dict[str, Any]:
    """
    Agent 6 Portfolio Health Engine:
    Calculates Diversification Score, Sector Concentration, Portfolio Beta,
    Volatility, Cash Allocation, Risk Rating, and Overall Health Score (0-100).
    """
    holdings = portfolio.get("holdings", [])
    cash = float(portfolio.get("cash_available", 100000.0))
    
    # 1. Total holdings value & position sizes
    holdings_value = 0.0
    position_values = {}
    sector_values = {}
    
    for h in holdings:
        qty = float(h.get("quantity", 0))
        avg_cost = float(h.get("average_price", h.get("entryPrice", 0.0)))
        current_price = float(h.get("last_price", h.get("close", avg_cost)))
        ticker = h.get("trading_symbol", h.get("ticker", "")).upper()
        sector = h.get("sector", "Other") or "Other"
        
        pos_val = qty * current_price
        holdings_value += pos_val
        position_values[ticker] = pos_val
        sector_values[sector] = sector_values.get(sector, 0.0) + pos_val
        
    total_val = cash + holdings_value
    if total_val <= 0:
        total_val = 100000.0 # Default fallback
        
    cash_pct = (cash / total_val) * 100.0
    
    # 2. Diversification Score & Concentration
    num_stocks = len(position_values)
    
    # Sector weightings
    sector_exposures = {}
    hhi_sector = 0.0
    for sec, val in sector_values.items():
        weight = val / total_val
        hhi_sector += weight ** 2
        sector_exposures[sec] = round(weight * 100, 2)
        
    # Stock weightings
    stock_exposures = {}
    hhi_stock = 0.0
    for tick, val in position_values.items():
        weight = val / total_val
        hhi_stock += weight ** 2
        stock_exposures[tick] = round(weight * 100, 2)
        
    # Base Diversification Score
    div_score = 100.0
    if num_stocks == 0:
        div_score = 0.0
    elif num_stocks == 1:
        div_score -= 40.0
    elif num_stocks <= 4:
        div_score -= 20.0
    elif num_stocks <= 8:
        div_score -= 5.0
        
    # Concentration penalties
    if hhi_sector > 0.40:
        div_score -= 25.0
    elif hhi_sector > 0.25:
        div_score -= 10.0
        
    if hhi_stock > 0.30:
        div_score -= 25.0
    elif hhi_stock > 0.15:
        div_score -= 10.0
        
    div_score = max(10.0, min(100.0, div_score)) if num_stocks > 0 else 0.0
    
    # 3. Portfolio Beta and Volatility Calculations
    # Fetch Nifty 50 Index candles as base benchmark for Beta
    nifty_returns = pd.Series(dtype=float)
    try:
        n_res = upstox_client.fetch_historical_candles("^NSEI", "day")
        if n_res and "candles" in n_res:
            n_closes = [float(c[4]) for c in reversed(n_res["candles"])]
            nifty_returns = pd.Series(n_closes).pct_change().dropna().tail(100)
    except Exception as e:
        logger.warning(f"Failed to fetch Nifty index for beta: {e}")
        
    stock_betas = {}
    stock_vols = {}
    
    for ticker in position_values.keys():
        beta = 1.0 # Default
        vol = 20.0 # Default
        try:
            s_res = upstox_client.fetch_historical_candles(ticker, "day")
            if s_res and "candles" in s_res:
                s_closes = [float(c[4]) for c in reversed(s_res["candles"])]
                s_returns = pd.Series(s_closes).pct_change().dropna().tail(100)
                
                # Volatility
                std = s_returns.std()
                if not np.isnan(std):
                    vol = std * np.sqrt(252) * 100.0
                    
                # Beta against Nifty 50
                if len(nifty_returns) > 10 and len(s_returns) > 10:
                    # Align returns on indexes
                    min_len = min(len(nifty_returns), len(s_returns))
                    cov = np.cov(s_returns.tail(min_len), nifty_returns.tail(min_len))
                    idx_var = cov[1, 1]
                    if idx_var > 0:
                        beta = cov[0, 1] / idx_var
        except Exception as e:
            logger.warning(f"Error computing beta/vol for {ticker}: {e}")
            
        stock_betas[ticker] = round(float(beta), 2)
        stock_vols[ticker] = round(float(vol), 2)
        
    # Calculate weighted averages
    weighted_beta = 0.0
    weighted_vol = 0.0
    total_held_val = sum(position_values.values())
    
    if total_held_val > 0:
        for tick, val in position_values.items():
            pos_weight = val / total_held_val
            weighted_beta += stock_betas[tick] * pos_weight
            weighted_vol += stock_vols[tick] * pos_weight
    else:
        weighted_beta = 1.0
        weighted_vol = 15.0
        
    # 4. Overall Portfolio Risk Rating
    if weighted_beta > 1.25 or weighted_vol > 26.0 or hhi_stock > 0.35:
        risk_rating = "Critical"
    elif weighted_beta > 1.1 or weighted_vol > 18.0:
        risk_rating = "High"
    elif weighted_beta < 0.85 and weighted_vol < 12.0:
        risk_rating = "Low"
    else:
        risk_rating = "Medium"
        
    # 5. Cash Allocation Score
    # Optimal cash is 10% to 25% of total portfolio value
    cash_score = 100.0
    if cash_pct > 40.0:
        cash_score -= (cash_pct - 40.0) * 1.5
    elif cash_pct < 10.0:
        cash_score -= (10.0 - cash_pct) * 4.0
    cash_score = max(10.0, min(100.0, cash_score))
    
    # 6. Overall Health Score (0-100)
    # Weighted average of Diversification (30%), Cash (20%), Volatility (25%), Concentration HHI (25%)
    vol_score = max(0.0, 100.0 - max(0.0, weighted_vol - 12.0) * 3.0)
    conc_score = max(0.0, 100.0 - max(0.0, hhi_stock - 0.1) * 300.0)
    
    overall_health = (div_score * 0.30) + (cash_score * 0.20) + (vol_score * 0.25) + (conc_score * 0.25)
    overall_health = max(0.0, min(100.0, overall_health))
    
    # 7. Diversification engine output details (Task 4)
    overweight_sectors = []
    underweight_sectors = []
    
    for sec, exp in sector_exposures.items():
        if exp > 35.0:
            overweight_sectors.append(sec)
        elif exp < 5.0 and num_stocks > 3:
            underweight_sectors.append(sec)
            
    single_stock_concentration = []
    for tick, exp in stock_exposures.items():
        if exp > 25.0:
            single_stock_concentration.append(tick)
            
    return {
        "overall_health_score": round(overall_health, 1),
        "diversification_score": round(div_score, 1),
        "portfolio_beta": round(weighted_beta, 2),
        "portfolio_volatility": round(weighted_vol, 1),
        "cash_allocation_pct": round(cash_pct, 1),
        "risk_rating": risk_rating,
        "sector_concentration": sector_exposures,
        "stock_concentration": stock_exposures,
        "diversification_engine": {
            "overweight_sectors": overweight_sectors,
            "underweight_sectors": underweight_sectors,
            "single_stock_concentration": single_stock_concentration,
            "hhi_stock": round(hhi_stock, 3),
            "hhi_sector": round(hhi_sector, 3)
        },
        "stock_betas": stock_betas,
        "stock_vols": stock_vols,
        "holdings_count": num_stocks
    }
