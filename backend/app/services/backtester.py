import logging
import numpy as np
import pandas as pd
import datetime
from typing import Dict, Any, List, Tuple
from app.db import db
from app.data_sources.market_data import upstox_client
from app.services.technical_indicators import compute_local_indicators

logger = logging.getLogger(__name__)

def run_monte_carlo(trades: List[float], initial_capital: float = 100000.0, num_paths: int = 1000, path_len: int = 50) -> Dict[str, Any]:
    """
    Runs Monte Carlo simulation using the empirical trade returns distribution.
    Calculates probability of profit, worst case drawdown, expected return range, and risk of ruin.
    """
    if not trades:
        return {
            "probability_of_profit": 50.0,
            "worst_case_drawdown": 0.0,
            "expected_return_range": [0.0, 0.0],
            "risk_of_ruin": 0.0
        }
        
    returns = np.array(trades)
    paths = []
    
    ruined_count = 0
    drawdowns = []
    final_values = []
    
    for _ in range(num_paths):
        # Bootstrap sample trade returns
        sampled = np.random.choice(returns, size=path_len, replace=True)
        equity = [initial_capital]
        current_val = initial_capital
        
        ruined = False
        peak = initial_capital
        max_dd = 0.0
        
        for r in sampled:
            current_val = current_val * (1.0 + r)
            equity.append(current_val)
            
            if current_val < initial_capital * 0.20:
                ruined = True
                
            if current_val > peak:
                peak = current_val
            dd = (peak - current_val) / peak if peak > 0 else 0.0
            if dd > max_dd:
                max_dd = dd
                
        if ruined:
            ruined_count += 1
            
        drawdowns.append(max_dd)
        final_values.append(current_val)
        
    final_values = np.array(final_values)
    profits = final_values > initial_capital
    prob_profit = (np.sum(profits) / num_paths) * 100.0
    risk_of_ruin = (ruined_count / num_paths) * 100.0
    worst_dd = float(np.max(drawdowns)) * 100.0
    
    # Expected return range (10th to 90th percentile)
    p10 = float(np.percentile(final_values, 10))
    p90 = float(np.percentile(final_values, 90))
    
    return {
        "probability_of_profit": round(prob_profit, 1),
        "worst_case_drawdown": round(worst_dd, 1),
        "expected_return_range": [round(p10, 2), round(p90, 2)],
        "risk_of_ruin": round(risk_of_ruin, 2)
    }

def calculate_backtest_metrics(
    equity: List[float], 
    trades: List[Dict[str, Any]], 
    dates: List[str], 
    initial_capital: float
) -> Dict[str, Any]:
    """
    Computes standard performance metrics for a backtest equity curve.
    """
    if len(equity) < 2:
        return {}
        
    total_return = ((equity[-1] - initial_capital) / initial_capital) * 100.0
    
    # Annualized return (CAGR)
    days = len(dates)
    years = days / 252.0 if days > 0 else 1.0
    cagr = (((equity[-1] / initial_capital) ** (1.0 / years)) - 1.0) * 100.0 if equity[-1] > 0 and years > 0 else 0.0
    
    # Trades analysis
    winners = [t for t in trades if t["profit_loss_pct"] > 0]
    losers = [t for t in trades if t["profit_loss_pct"] <= 0]
    
    win_rate = (len(winners) / len(trades)) * 100.0 if trades else 0.0
    
    gross_profits = sum([t["profit_loss_val"] for t in winners])
    gross_losses = abs(sum([t["profit_loss_val"] for t in losers]))
    profit_factor = gross_profits / gross_losses if gross_losses > 0 else (gross_profits if gross_profits > 0 else 1.0)
    
    # Drawdowns
    peaks = []
    current_peak = initial_capital
    max_dd = 0.0
    for v in equity:
        if v > current_peak:
            current_peak = v
        dd = (current_peak - v) / current_peak if current_peak > 0 else 0.0
        if dd > max_dd:
            max_dd = dd
            
    # Daily returns for Sharpe / Sortino
    eq_series = pd.Series(equity)
    daily_returns = eq_series.pct_change().dropna()
    
    # Sharpe Ratio (assumes risk free rate is 5% annualized = ~0.02% daily)
    avg_daily_ret = daily_returns.mean()
    std_daily_ret = daily_returns.std()
    
    sharpe = 0.0
    if std_daily_ret > 0:
        sharpe = (avg_daily_ret * 252.0 - 0.05) / (std_daily_ret * np.sqrt(252.0))
        
    # Sortino Ratio (downside volatility only)
    downside_returns = daily_returns[daily_returns < 0]
    downside_std = downside_returns.std()
    sortino = 0.0
    if downside_std > 0:
        sortino = (avg_daily_ret * 252.0 - 0.05) / (downside_std * np.sqrt(252.0))
        
    avg_win = np.mean([t["profit_loss_pct"] for t in winners]) * 100.0 if winners else 0.0
    avg_loss = np.mean([t["profit_loss_pct"] for t in losers]) * 100.0 if losers else 0.0
    
    avg_holding = np.mean([t["holding_period"] for t in trades]) if trades else 0.0
    expectancy = (win_rate / 100.0 * avg_win) + ((100.0 - win_rate) / 100.0 * avg_loss)
    
    # Equity curve values mapping
    equity_curve = [{"date": dates[i], "value": round(equity[i], 2)} for i in range(len(equity))]
    
    return {
        "total_return": round(total_return, 2),
        "annual_return": round(cagr, 2),
        "win_rate": round(win_rate, 1),
        "profit_factor": round(profit_factor, 2),
        "max_drawdown": round(max_dd * 100.0, 2),
        "sharpe_ratio": round(sharpe, 2),
        "sortino_ratio": round(sortino, 2),
        "avg_holding_period": round(avg_holding, 1),
        "avg_winner_pct": round(avg_win, 2),
        "avg_loser_pct": round(avg_loss, 2),
        "expectancy": round(expectancy, 2),
        "equity_curve": equity_curve,
        "trades_count": len(trades)
    }

def run_backtest_strategy(
    strategy_name: str,
    closes: List[float],
    highs: List[float],
    lows: List[float],
    volumes: List[float],
    dates: List[str],
    initial_capital: float = 100000.0,
    commission: float = 0.0005, # 0.05%
    slippage: float = 0.0005    # 0.05%
) -> Dict[str, Any]:
    """
    Backtests specified technical strategy across price candles.
    """
    n = len(closes)
    if n < 55:
        return {}
        
    df = pd.DataFrame({
        "close": closes,
        "high": highs,
        "low": lows,
        "volume": volumes
    })
    
    # 1. Compute Indicators
    df["ema20"] = df["close"].ewm(span=20, adjust=False).mean()
    df["ema50"] = df["close"].ewm(span=50, adjust=False).mean()
    
    # RSI
    delta = df["close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df["rsi"] = 100 - (100 / (1 + rs))
    df["rsi"] = df["rsi"].fillna(50)
    
    # MACD
    ema12 = df["close"].ewm(span=12, adjust=False).mean()
    ema26 = df["close"].ewm(span=26, adjust=False).mean()
    df["macd"] = ema12 - ema26
    df["signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    
    # ATR (14)
    high_low = df["high"] - df["low"]
    high_close = np.abs(df["high"] - df["close"].shift())
    low_close = np.abs(df["low"] - df["close"].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    df["atr"] = true_range.rolling(window=14).mean().fillna(df["close"] * 0.02)
    
    # Supertrend
    multiplier = 3.0
    hl2 = (df["high"] + df["low"]) / 2.0
    df["basic_ub"] = hl2 + multiplier * df["atr"]
    df["basic_lb"] = hl2 - multiplier * df["atr"]
    
    # Custom Supertrend logic
    final_ub = [0.0] * n
    final_lb = [0.0] * n
    supertrend = [0.0] * n
    trend = [1] * n # 1=bullish, -1=bearish
    
    for i in range(1, n):
        # Upper band
        if df["basic_ub"].iloc[i] < final_ub[i-1] or df["close"].iloc[i-1] > final_ub[i-1]:
            final_ub[i] = df["basic_ub"].iloc[i]
        else:
            final_ub[i] = final_ub[i-1]
            
        # Lower band
        if df["basic_lb"].iloc[i] > final_lb[i-1] or df["close"].iloc[i-1] < final_lb[i-1]:
            final_lb[i] = df["basic_lb"].iloc[i]
        else:
            final_lb[i] = final_lb[i-1]
            
        # Trend
        if trend[i-1] == 1:
            if df["close"].iloc[i] < final_lb[i]:
                trend[i] = -1
                supertrend[i] = final_ub[i]
            else:
                trend[i] = 1
                supertrend[i] = final_lb[i]
        else:
            if df["close"].iloc[i] > final_ub[i]:
                trend[i] = 1
                supertrend[i] = final_lb[i]
            else:
                trend[i] = -1
                supertrend[i] = final_ub[i]
                
    df["supertrend"] = supertrend
    df["supertrend_direction"] = trend
    
    # Breakout high/low
    df["high20"] = df["close"].rolling(20).max().shift(1)
    df["low20"] = df["close"].rolling(20).min().shift(1)
    df["vol_avg"] = df["volume"].rolling(20).mean().shift(1)
    
    # 2. Simulate Backtest
    capital = initial_capital
    position = 0.0
    entry_price = 0.0
    entry_idx = 0
    
    equity = [initial_capital] * n
    trades = []
    
    for i in range(50, n):
        price = closes[i]
        
        # Check Strategy Signal
        buy_signal = False
        sell_signal = False
        
        if strategy_name == "EMA Crossover":
            # EMA20 cross above EMA50
            if df["ema20"].iloc[i] > df["ema50"].iloc[i] and df["ema20"].iloc[i-1] <= df["ema50"].iloc[i-1]:
                buy_signal = True
            elif df["ema20"].iloc[i] < df["ema50"].iloc[i] and df["ema20"].iloc[i-1] >= df["ema50"].iloc[i-1]:
                sell_signal = True
                
        elif strategy_name == "Supertrend + MACD":
            # Supertrend bullish + MACD cross above Signal
            if df["supertrend_direction"].iloc[i] == 1 and df["macd"].iloc[i] > df["signal"].iloc[i] and df["macd"].iloc[i-1] <= df["signal"].iloc[i-1]:
                buy_signal = True
            elif df["supertrend_direction"].iloc[i] == -1 or (df["macd"].iloc[i] < df["signal"].iloc[i]):
                sell_signal = True
                
        elif strategy_name == "RSI Reversal":
            # RSI oversold turn up
            if df["rsi"].iloc[i] > 30 and df["rsi"].iloc[i-1] <= 30:
                buy_signal = True
            elif df["rsi"].iloc[i] < 70 and df["rsi"].iloc[i-1] >= 70:
                sell_signal = True
                
        elif strategy_name == "Breakout + Volume":
            # 20-day high breakout with high volume
            if df["close"].iloc[i] > df["high20"].iloc[i] and df["volume"].iloc[i] > 1.5 * df["vol_avg"].iloc[i]:
                buy_signal = True
            elif df["close"].iloc[i] < df["low20"].iloc[i]:
                sell_signal = True
                
        elif strategy_name == "Momentum Pullback":
            # Uptrend (close > EMA50) and RSI pulls back under 45
            if df["close"].iloc[i] > df["ema50"].iloc[i] and df["rsi"].iloc[i] < 45 and df["rsi"].iloc[i] > df["rsi"].iloc[i-1]:
                buy_signal = True
            elif df["rsi"].iloc[i] > 70 or df["close"].iloc[i] < df["ema50"].iloc[i]:
                sell_signal = True
                
        elif strategy_name == "Institutional AI Recommendation":
            # New optimized consensus ensemble simulation (Task 2, 3 & 4)
            bo_buy = df["close"].iloc[i] > df["high20"].iloc[i] and df["volume"].iloc[i] > 1.2 * df["vol_avg"].iloc[i]
            bo_sell = df["close"].iloc[i] < df["low20"].iloc[i]
            
            st_buy = df["supertrend_direction"].iloc[i] == 1 and df["macd"].iloc[i] > df["signal"].iloc[i]
            st_sell = df["supertrend_direction"].iloc[i] == -1 or df["macd"].iloc[i] < df["signal"].iloc[i]
            
            ema_buy = df["ema20"].iloc[i] > df["ema50"].iloc[i]
            ema_sell = df["ema20"].iloc[i] < df["ema50"].iloc[i]
            
            mom_buy = df["close"].iloc[i] > df["ema50"].iloc[i] and df["rsi"].iloc[i] < 45 and df["rsi"].iloc[i] > df["rsi"].iloc[i-1]
            mom_sell = df["rsi"].iloc[i] > 70 or df["close"].iloc[i] < df["ema50"].iloc[i]
            
            rsi_buy = df["rsi"].iloc[i] < 35
            rsi_sell = df["rsi"].iloc[i] > 65
            
            score_bo = 100.0 if bo_buy else 0.0 if bo_sell else 50.0
            score_st = 100.0 if st_buy else 0.0 if st_sell else 50.0
            score_ema = 100.0 if ema_buy else 0.0 if ema_sell else 50.0
            score_mom = 100.0 if mom_buy else 0.0 if mom_sell else 50.0
            score_rsi = 100.0 if rsi_buy else 0.0 if rsi_sell else 50.0
            
            # Weighted average consensus score (Task 4)
            consensus_score = (score_bo * 0.35) + (score_st * 0.25) + (score_ema * 0.15) + (score_mom * 0.15) + (score_rsi * 0.10)
            
            if consensus_score >= 70.0:
                buy_signal = True
            elif consensus_score < 45.0:
                sell_signal = True
                
            # Consensus Gate Overrides (Task 3)
            if buy_signal:
                # Block buy if top strategies indicate sells or volatility is extreme (ATR > 6% of close)
                atr_pct = (df["atr"].iloc[i] / df["close"].iloc[i]) * 100.0
                if bo_sell or st_sell or atr_pct > 6.0:
                    buy_signal = False
                
        # Execution
        if position == 0:
            if buy_signal:
                # Buy
                trade_price = price * (1.0 + slippage)
                cost = trade_price * commission
                position = (capital - cost) / trade_price
                entry_price = trade_price
                entry_idx = i
                capital = 0.0
        else:
            # Check exit
            if sell_signal:
                # Sell
                trade_price = price * (1.0 - slippage)
                proceeds = position * trade_price
                cost = proceeds * commission
                net_proceeds = proceeds - cost
                
                profit_loss = net_proceeds - (position * entry_price)
                profit_loss_pct = (trade_price - entry_price) / entry_price
                
                trades.append({
                    "buy_date": dates[entry_idx],
                    "sell_date": dates[i],
                    "buy_price": round(entry_price, 2),
                    "sell_price": round(trade_price, 2),
                    "profit_loss_val": round(profit_loss, 2),
                    "profit_loss_pct": round(profit_loss_pct, 4),
                    "holding_period": i - entry_idx
                })
                
                capital = net_proceeds
                position = 0.0
                
        # Update equity
        if position > 0:
            equity[i] = position * price
        else:
            equity[i] = capital
            
    # If still holding position at end, liquidate virtually
    if position > 0:
        price = closes[-1]
        trade_price = price * (1.0 - slippage)
        proceeds = position * trade_price
        cost = proceeds * commission
        net_proceeds = proceeds - cost
        profit_loss = net_proceeds - (position * entry_price)
        profit_loss_pct = (trade_price - entry_price) / entry_price
        trades.append({
            "buy_date": dates[entry_idx],
            "sell_date": dates[-1],
            "buy_price": round(entry_price, 2),
            "sell_price": round(trade_price, 2),
            "profit_loss_val": round(profit_loss, 2),
            "profit_loss_pct": round(profit_loss_pct, 4),
            "holding_period": n - 1 - entry_idx
        })
        equity[-1] = net_proceeds
        
    metrics = calculate_backtest_metrics(equity, trades, dates, initial_capital)
    
    # Run Monte Carlo if trades occurred
    trade_pcts = [t["profit_loss_pct"] for t in trades]
    mc = run_monte_carlo(trade_pcts, initial_capital)
    
    return {
        "strategy": strategy_name,
        "metrics": metrics,
        "monte_carlo": mc,
        "trades": trades
    }
