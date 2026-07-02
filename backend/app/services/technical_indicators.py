import logging
import pandas as pd
import numpy as np
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

def compute_local_indicators(
    history_close: List[float],
    history_high: List[float],
    history_low: List[float],
    history_volume: List[float]
) -> Dict[str, Any]:
    """
    Computes technical indicators locally using Python (pandas and numpy).
    Ensures that no fallbacks like EMA=0 or ATR=0 are returned if valid data is present.
    
    Inputs:
        history_close: chronological list of close prices (oldest to newest)
        history_high: chronological list of high prices (oldest to newest)
        history_low: chronological list of low prices (oldest to newest)
        history_volume: chronological list of volumes (oldest to newest)
    
    Returns:
        A dictionary containing computed indicator values.
    """
    n = len(history_close)
    if n == 0:
        return {
            "ema20": 0.0,
            "ema50": 0.0,
            "rsi": 50.0,
            "macd_val": 0.0,
            "signal_val": 0.0,
            "macd_desc": "Neutral",
            "atr": 0.0,
            "bollinger_upper": 0.0,
            "bollinger_middle": 0.0,
            "bollinger_lower": 0.0,
            "support": 0.0,
            "resistance": 0.0,
            "volume_surge": 1.0,
            "average_volume": 0.0,
            "latest_volume": 0.0,
            "sma50": 0.0,
            "sma200": 0.0,
            "breakout_detected": False
        }

    # Use Series/DataFrames for indicator calculation
    close_s = pd.Series(history_close, dtype=float)
    high_s = pd.Series(history_high, dtype=float) if history_high else close_s
    low_s = pd.Series(history_low, dtype=float) if history_low else close_s
    vol_s = pd.Series(history_volume, dtype=float) if history_volume else pd.Series([1.0] * n)

    # 1. EMA 20 & EMA 50
    ema20_series = close_s.ewm(span=20, adjust=False).mean()
    ema50_series = close_s.ewm(span=50, adjust=False).mean()
    
    latest_ema20 = ema20_series.iloc[-1] if n >= 1 else close_s.iloc[-1]
    latest_ema50 = ema50_series.iloc[-1] if n >= 1 else close_s.iloc[-1]

    # 2. SMAs (50, 200)
    sma50_series = close_s.rolling(window=min(50, n)).mean()
    sma200_series = close_s.rolling(window=min(200, n)).mean()
    latest_sma50 = sma50_series.iloc[-1] if not sma50_series.empty else close_s.iloc[-1]
    latest_sma200 = sma200_series.iloc[-1] if not sma200_series.empty else close_s.iloc[-1]

    # 3. RSI (14)
    delta = close_s.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
    rs = avg_gain / avg_loss.clip(lower=1e-9)
    rsi_series = 100 - (100 / (1 + rs))
    
    latest_rsi = rsi_series.iloc[-1] if n > 1 else 50.0
    if pd.isna(latest_rsi):
        latest_rsi = 50.0

    # 4. MACD (12, 26, 9)
    ema12 = close_s.ewm(span=12, adjust=False).mean()
    ema26 = close_s.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    
    latest_macd = macd_line.iloc[-1] if n >= 1 else 0.0
    latest_signal = signal_line.iloc[-1] if n >= 1 else 0.0
    
    if n > 1:
        if latest_macd > latest_signal:
            macd_desc = "Bullish Crossover"
        elif latest_macd < latest_signal:
            macd_desc = "Bearish Crossover"
        else:
            macd_desc = "Neutral"
    else:
        macd_desc = "Neutral"

    # 5. ATR (14)
    tr1 = high_s - low_s
    tr2 = (high_s - close_s.shift(1)).abs()
    tr3 = (low_s - close_s.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    atr_series = tr.ewm(alpha=1/14, adjust=False).mean()
    latest_atr = atr_series.iloc[-1] if n > 1 else (high_s.iloc[-1] - low_s.iloc[-1])
    if pd.isna(latest_atr) or latest_atr <= 0:
        latest_atr = max(0.01, high_s.iloc[-1] - low_s.iloc[-1])

    # 6. Bollinger Bands (20, 2)
    sma20 = close_s.rolling(window=min(20, n)).mean()
    std20 = close_s.rolling(window=min(20, n)).std()
    std20 = std20.fillna(0.0)
    
    bollinger_upper_series = sma20 + (2 * std20)
    bollinger_middle_series = sma20
    bollinger_lower_series = sma20 - (2 * std20)
    
    latest_upper = bollinger_upper_series.iloc[-1]
    latest_middle = bollinger_middle_series.iloc[-1]
    latest_lower = bollinger_lower_series.iloc[-1]

    # 7. Support & Resistance (min/max of last 20 closes)
    support_window = min(20, n)
    latest_support = float(close_s.iloc[-support_window:].min())
    latest_resistance = float(close_s.iloc[-support_window:].max())

    # 8. Volume Analysis
    latest_vol = float(vol_s.iloc[-1])
    avg_vol_20 = vol_s.rolling(window=min(20, n)).mean().iloc[-1]
    volume_surge = latest_vol / avg_vol_20 if avg_vol_20 > 0 else 1.0

    # 9. Breakout detection (Crossing resistance with volume surge > 1.3x)
    prev_20_max = close_s.iloc[-21:-1].max() if n >= 21 else close_s.max()
    breakout_detected = bool(close_s.iloc[-1] > prev_20_max and volume_surge > 1.3)

    return {
        "ema20": round(float(latest_ema20), 2),
        "ema50": round(float(latest_ema50), 2),
        "rsi": round(float(latest_rsi), 2),
        "macd_val": round(float(latest_macd), 2),
        "signal_val": round(float(latest_signal), 2),
        "macd_desc": macd_desc,
        "atr": round(float(latest_atr), 2),
        "bollinger_upper": round(float(latest_upper), 2),
        "bollinger_middle": round(float(latest_middle), 2),
        "bollinger_lower": round(float(latest_lower), 2),
        "support": round(latest_support, 2),
        "resistance": round(latest_resistance, 2),
        "volume_surge": round(float(volume_surge), 2),
        "average_volume": round(float(avg_vol_20), 2),
        "latest_volume": latest_vol,
        "sma50": round(float(latest_sma50), 2),
        "sma200": round(float(latest_sma200), 2),
        "breakout_detected": breakout_detected
    }
