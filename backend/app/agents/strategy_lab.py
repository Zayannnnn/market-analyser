import logging
import google.generativeai as genai
import json
import time
from typing import Dict, Any, List
from app.config import settings
from app.db import db
from app.agents.explanation import repair_json_text

logger = logging.getLogger(__name__)

# Configure Gemini
genai.configure(api_key=settings.gemini_api_key)

def compare_backtest_strategies(ticker: str, strategies_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Agent 7.0: AI Strategy Laboratory Comparator.
    Submits backtest results of all strategies for a ticker to Gemini,
    requesting comparison analysis, risk scores, and suitability.
    """
    logger.info(f"AI Strategy Laboratory comparison sequence initiated for {ticker}...")
    
    # 1. Format strategy summaries for prompt
    summaries = []
    for s in strategies_results:
        strategy_name = s.get("strategy", "")
        metrics = s.get("metrics", {})
        mc = s.get("monte_carlo", {})
        
        summary = f"""
        Strategy: {strategy_name}
        - Total Return: {metrics.get('total_return')}%
        - Annual Return (CAGR): {metrics.get('annual_return')}%
        - Win Rate: {metrics.get('win_rate')}%
        - Profit Factor: {metrics.get('profit_factor')}
        - Max Drawdown: {metrics.get('max_drawdown')}%
        - Sharpe Ratio: {metrics.get('sharpe_ratio')}
        - Sortino Ratio: {metrics.get('sortino_ratio')}
        - Expectancy: {metrics.get('expectancy')}
        - Number of Trades: {metrics.get('trades_count')}
        - Monte Carlo Prob of Profit: {mc.get('probability_of_profit')}%
        - Monte Carlo Risk of Ruin: {mc.get('risk_of_ruin')}%
        """
        summaries.append(summary.strip())
        
    prompt = f"""
    You are an institutional quant researcher and strategy validator analyzing backtest results of multiple strategies for stock: {ticker}.
    Review the following backtesting performance parameters:
    
    {chr(10).join(summaries)}
    
    Provide your comparative assessment in raw JSON format exactly matching the following keys:
    - "best_strategy": "Name of the strategy with the best risk-adjusted profile"
    - "worst_strategy": "Name of the strategy with the poorest performance or excessive drawdown"
    - "confidence": "High / Medium / Low", // overall analyst confidence in the best strategy
    - "risk": "Low / Moderate / High", // drawdown and tail risk assessment
    - "market_suitability": "E.g. Trending markets, volatile markets, range-bound markets, etc."
    - "reasoning": "A brief explanation of why the best strategy out-performed and why the worst strategy failed."
    
    Return ONLY the raw JSON object. Do not include markdown blocks, comments, or extra text.
    """
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            logger.info(f"Dispatching AI strategy comparison to Gemini (Attempt {attempt + 1}/{max_retries})...")
            model = genai.GenerativeModel("gemini-2.5-flash")
            response = model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            
            repaired = repair_json_text(response.text.strip())
            result = json.loads(repaired)
            
            comparison = {
                "best_strategy": str(result.get("best_strategy", "")),
                "worst_strategy": str(result.get("worst_strategy", "")),
                "confidence": str(result.get("confidence", "Medium")),
                "risk": str(result.get("risk", "Moderate")),
                "market_suitability": str(result.get("market_suitability", "")),
                "reasoning": str(result.get("reasoning", "")),
                "analyzed_at": time.time(),
                "ticker": ticker
            }
            
            # Save results in Firestore strategy_comparisons collection
            try:
                db.collection("strategy_comparisons").document(ticker).set(comparison)
            except Exception as fe:
                logger.error(f"Failed to save strategy comparison in Firestore for {ticker}: {fe}")
                
            return comparison
            
        except Exception as e:
            logger.warning(f"Error parsing Gemini strategy comparison on attempt {attempt + 1}: {e}")
            if attempt == max_retries - 1:
                logger.error(f"Gemini strategy comparison retries exhausted: {e}")
            else:
                time.sleep(1.0)
                
    return get_fallback_strategy_comparison(ticker, strategies_results)

def get_fallback_strategy_comparison(ticker: str, strategies_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Returns a default structure on comparison failure."""
    best = "EMA Crossover"
    best_ret = -999.0
    for s in strategies_results:
        ret = s.get("metrics", {}).get("total_return", 0.0)
        if ret > best_ret:
            best_ret = ret
            best = s.get("strategy", best)
            
    return {
        "best_strategy": best,
        "worst_strategy": "Momentum Pullback",
        "confidence": "Medium",
        "risk": "Moderate",
        "market_suitability": "Trending asset cycles.",
        "reasoning": f"Strategy comparison resolved best-performing historical return as {best} over the backtest timeline.",
        "analyzed_at": time.time(),
        "ticker": ticker
    }
