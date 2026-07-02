import datetime
import logging
from typing import Any, Dict

import httpx
import yfinance as yf

logger = logging.getLogger(__name__)

CHART_PERIOD_MAP = {
    "1D": "5d",
    "1W": "1mo",
    "1M": "3mo",
    "3M": "6mo",
    "6M": "1y",
    "1Y": "2y",
    "5Y": "5y",
    "MAX": "max",
}


def _parse_chart_payload(data: Dict[str, Any], provider_ticker: str) -> Dict[str, Any]:
    result = data["chart"]["result"][0]
    meta = result["meta"]
    timestamps = result.get("timestamp", [])
    quote = result.get("indicators", {}).get("quote", [{}])[0]
    closes_raw = quote.get("close", [])
    volumes_raw = quote.get("volume", [])

    history_close = []
    history_volume = []
    history_dates = []
    last_close = meta.get("regularMarketPrice")
    last_volume = meta.get("regularMarketVolume", 0.0)
    valid_close_seen = last_close is not None

    for idx, ts in enumerate(timestamps):
        close_val = closes_raw[idx] if idx < len(closes_raw) else None
        volume_val = volumes_raw[idx] if idx < len(volumes_raw) else None
        if close_val is not None:
            last_close = float(close_val)
            valid_close_seen = True
        if volume_val is not None:
            last_volume = float(volume_val)
        if last_close is None:
            continue
        history_close.append(float(last_close))
        history_volume.append(float(last_volume))
        history_dates.append(
            datetime.datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d")
        )

    if not history_close or not valid_close_seen:
        raise ValueError(f"Chart API returned empty history for {provider_ticker}")

    price = float(meta.get("regularMarketPrice") or history_close[-1])
    prev_price = history_close[-2] if len(history_close) > 1 else price
    change = ((price - prev_price) / prev_price) * 100 if prev_price > 0 else 0.0

    return {
        "price": price,
        "change": change,
        "volume": float(last_volume),
        "history_close": history_close,
        "history_volume": history_volume,
        "history_dates": history_dates,
    }


def _fetch_chart(provider_ticker: str, yahoo_range: str) -> Dict[str, Any]:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    for host in ("query2.finance.yahoo.com", "query1.finance.yahoo.com"):
        url = f"https://{host}/v8/finance/chart/{provider_ticker}?range={yahoo_range}&interval=1d"
        logger.info("Live chart request: %s", url)
        try:
            response = httpx.get(url, headers=headers, timeout=15.0)
            if response.status_code == 200:
                payload = response.json()
                if payload.get("chart", {}).get("result"):
                    return _parse_chart_payload(payload, provider_ticker)
        except httpx.HTTPError as exc:
            logger.warning("Live chart request failed for %s via %s: %s", provider_ticker, host, exc)
    raise ValueError(f"Live chart data unavailable for {provider_ticker}")


def _fetch_profile(provider_ticker: str) -> Dict[str, Any]:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    for host in ("query1.finance.yahoo.com", "query2.finance.yahoo.com"):
        try:
            url = f"https://{host}/v7/finance/quote?symbols={provider_ticker}"
            response = httpx.get(url, headers=headers, timeout=10.0)
            if response.status_code == 200:
                result = response.json().get("quoteResponse", {}).get("result", [])
                if result:
                    quote = result[0]
                    raw_mcap = quote.get("marketCap")
                    raw_pe = quote.get("trailingPE") or quote.get("forwardPE")
                    return {
                        "market_cap": (float(raw_mcap) / 1e9) if raw_mcap else None,
                        "pe_ratio": float(raw_pe) if raw_pe else None,
                        "sector": None,
                        "company_name": quote.get("longName") or quote.get("shortName"),
                        "revenue_growth": None,
                        "profit_growth": None,
                        "roe": None,
                        "debt_to_equity": None,
                    }
        except httpx.HTTPError as exc:
            logger.warning("Quote profile unavailable for %s via %s: %s", provider_ticker, host, exc)

    try:
        ticker = yf.Ticker(provider_ticker)
        info = ticker.info or {}
        try:
            fast_info = ticker.fast_info or {}
        except Exception:
            fast_info = {}
        raw_mcap = info.get("marketCap") or fast_info.get("market_cap")
        raw_pe = info.get("trailingPE") or info.get("forwardPE")
        return {
            "market_cap": (float(raw_mcap) / 1e9) if raw_mcap else None,
            "pe_ratio": float(raw_pe) if raw_pe else None,
            "sector": info.get("sector"),
            "company_name": info.get("longName") or info.get("shortName"),
            "revenue_growth": info.get("revenueGrowth"),
            "profit_growth": info.get("earningsGrowth") or info.get("earningsQuarterlyGrowth"),
            "roe": info.get("returnOnEquity"),
            "debt_to_equity": info.get("debtToEquity"),
        }
    except Exception as exc:
        logger.warning("Profile enrichment unavailable for %s: %s", provider_ticker, exc)
        return {
            "market_cap": None,
            "pe_ratio": None,
            "sector": None,
            "company_name": None,
            "revenue_growth": None,
            "profit_growth": None,
            "roe": None,
            "debt_to_equity": None,
        }


def fetch_live_quote(provider_ticker: str) -> Dict[str, Any]:
    """Live price metrics only. Raises if provider has no usable quote."""
    chart = _fetch_chart(provider_ticker, "5d")
    profile = _fetch_profile(provider_ticker)
    return {
        "price": chart["price"],
        "change": chart["change"],
        "volume": chart["volume"],
        "market_cap": profile["market_cap"],
        "pe_ratio": profile["pe_ratio"],
        "sector": profile["sector"],
        "provider_company_name": profile["company_name"],
        "revenue_growth": profile["revenue_growth"],
        "profit_growth": profile["profit_growth"],
        "roe": profile["roe"],
        "debt_to_equity": profile["debt_to_equity"],
    }


def fetch_price_history(provider_ticker: str, period: str = "1M") -> Dict[str, Any]:
    """Live OHLCV history for chart rendering. Raises if provider has no data."""
    yahoo_range = CHART_PERIOD_MAP.get(period.upper(), "3mo")
    chart = _fetch_chart(provider_ticker, yahoo_range)
    return {
        "period": period.upper(),
        "provider_ticker": provider_ticker,
        "history_close": chart["history_close"],
        "history_volume": chart["history_volume"],
        "history_dates": chart["history_dates"],
    }
