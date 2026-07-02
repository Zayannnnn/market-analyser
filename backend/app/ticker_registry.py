import json
from pathlib import Path
from typing import Dict, List, Optional

_MASTER_PATH = Path(__file__).parent / "data" / "stock_master.json"

with _MASTER_PATH.open(encoding="utf-8") as f:
    _MASTER_LIST: List[Dict[str, str]] = json.load(f)

TICKER_REGISTRY: Dict[str, Dict[str, object]] = {
    entry["ticker"]: {
        "company_name": entry["companyName"],
        "provider_ticker": entry["providerTicker"],
        "sector": entry.get("sector", ""),
        "search_terms": entry.get("searchTerms", []),
    }
    for entry in _MASTER_LIST
}

INDEX_REGISTRY: Dict[str, Dict[str, object]] = {
    "^NSEI": {"company_name": "Nifty 50", "provider_ticker": "^NSEI", "sector": "Index"},
    "^NSEBANK": {"company_name": "Nifty Bank", "provider_ticker": "^NSEBANK", "sector": "Index"},
    "^BSESN": {"company_name": "BSE Sensex", "provider_ticker": "^BSESN", "sector": "Index"},
    "^GSPC": {"company_name": "S&P 500", "provider_ticker": "^GSPC", "sector": "Index"},
    "^IXIC": {"company_name": "NASDAQ Composite", "provider_ticker": "^IXIC", "sector": "Index"},
}


def get_stock_master() -> List[Dict[str, str]]:
    return _MASTER_LIST


def resolve_ticker(ticker: str, include_indexes: bool = True) -> Optional[Dict[str, object]]:
    normalized = ticker.upper().strip()
    if normalized in TICKER_REGISTRY:
        return {"ticker": normalized, **TICKER_REGISTRY[normalized]}
    if include_indexes and normalized in INDEX_REGISTRY:
        return {"ticker": normalized, **INDEX_REGISTRY[normalized]}
    return None


def search_tickers(query: str, limit: int = 8) -> List[Dict[str, str]]:
    """Prefix match on ticker or company name only. No fuzzy or substring matching."""
    normalized = query.strip().upper()
    if not normalized:
        return []

    matches: List[tuple] = []
    for index, entry in enumerate(_MASTER_LIST):
        ticker = entry["ticker"]
        company_name = entry["companyName"]
        search_terms = [term.upper() for term in entry.get("searchTerms", [])]
        ticker_match = ticker.upper().startswith(normalized)
        company_match = company_name.upper().startswith(normalized)
        search_term_match = normalized in search_terms
        if ticker_match or company_match or search_term_match:
            priority = 0 if ticker_match else 1 if search_term_match else 2
            matches.append((priority, index, entry))

    matches.sort(key=lambda item: (item[0], item[1]))
    results: List[Dict[str, str]] = []
    for _, _, entry in matches[:limit]:
        results.append({
            "ticker": entry["ticker"],
            "company_name": entry["companyName"],
            "provider_ticker": entry["providerTicker"],
            "sector": entry.get("sector", ""),
        })
    return results
