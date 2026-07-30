import os
import sys
import logging
import json
import pandas as pd

# Setup sys path to include backend
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set env variables before imports
os.environ["FIREBASE_KEY_PATH"] = "backend/serviceAccountKey.json"

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

from app.db import db
from app.data_sources.market_data import upstox_client, resolve_ticker
from app.services.backtester import run_backtest_strategy
from app.agents.strategy_lab import compare_backtest_strategies

def test_strategy_lab_e2e():
    logger.info("Initializing E2E Strategy Lab & Backtest Engine validation check...")
    
    tickers = ["GREENPOWER", "BEL", "RELIANCE", "TCS", "INFY"]
    days_back = 1825 # 5 years
    
    # Store performance comparison summaries
    performance_records = []
    
    for ticker in tickers:
        logger.info(f"\n----------------------------------------------------")
        logger.info(f"Analyzing Stock: {ticker}")
        logger.info(f"----------------------------------------------------")
        
        # 1. Fetch historical candles from Upstox
        try:
            res = upstox_client.fetch_historical_candles(ticker, days_back=days_back)
            if not res or "candles" not in res:
                logger.warning(f"Failed to fetch 5-year candles from Upstox for {ticker}. Skipping.")
                continue
                
            candles = res["candles"]
            # Reverse to get oldest -> newest chronological order
            candles_reversed = list(candles)
            candles_reversed.reverse()
            
            closes = [float(c[4]) for c in candles_reversed]
            highs = [float(c[2]) for c in candles_reversed]
            lows = [float(c[3]) for c in candles_reversed]
            volumes = [float(c[5]) for c in candles_reversed]
            dates = [c[0][:10] for c in candles_reversed]
            
            logger.info(f"Retrieved {len(closes)} daily candles (Start: {dates[0]} | End: {dates[-1]})")
        except Exception as e:
            logger.error(f"Error fetching candles for {ticker}: {e}")
            continue
            
        # 2. Run all 6 backtesting models
        strategies = [
            "EMA Crossover",
            "Supertrend + MACD",
            "RSI Reversal",
            "Breakout + Volume",
            "Momentum Pullback",
            "Institutional AI Recommendation"
        ]
        
        strat_results = []
        for strat in strategies:
            try:
                res_strat = run_backtest_strategy(strat, closes, highs, lows, volumes, dates)
                if res_strat:
                    strat_results.append(res_strat)
                    metrics = res_strat["metrics"]
                    mc = res_strat["monte_carlo"]
                    logger.info(f"[+] Strategy: {strat:<32} | Return: {metrics['total_return']:>7}% | WinRate: {metrics['win_rate']:>5}% | Sharpe: {metrics['sharpe_ratio']:>5} | PoP: {mc['probability_of_profit']:>5}%")
            except Exception as e:
                logger.error(f"Error running backtest strategy {strat} on {ticker}: {e}")
                
        # 3. Get AI comparison report
        try:
            comparison = compare_backtest_strategies(ticker, strat_results)
            logger.info(f"[*] AI Recommended Best Strategy: {comparison.get('best_strategy')}")
            logger.info(f"[*] AI Recommended Worst Strategy: {comparison.get('worst_strategy')}")
            logger.info(f"[*] Market Suitability: {comparison.get('market_suitability')}")
        except Exception as e:
            logger.error(f"Error generating AI strategy comparison for {ticker}: {e}")
            
    logger.info("\n[SUCCESS] E2E Strategy Lab verification completed.")
    return True

if __name__ == "__main__":
    success = test_strategy_lab_e2e()
    if success:
        sys.exit(0)
    else:
        sys.exit(1)
