#!/usr/bin/env python3
"""Validate live quote data for key tickers."""

from app.ticker_registry import resolve_ticker
from app.data_sources.live_quotes import fetch_live_quote

TICKERS = ["HCLTECH", "BEL", "HFCL", "RELIANCE", "INFY"]


def main() -> None:
    print("=" * 60)
    print("STOCK VALIDATION")
    print("=" * 60)
    for ticker in TICKERS:
        entry = resolve_ticker(ticker)
        if not entry:
            print(f"{ticker}: NOT IN MASTER")
            continue
        provider = entry["provider_ticker"]
        print(f"\n{ticker} -> {provider}")
        try:
            live = fetch_live_quote(str(provider))
            print(f"  price:      ₹{live['price']:,.2f}")
            mcap = live.get("market_cap")
            print(f"  market_cap: {'₹' + format(mcap, '.2f') + ' B' if mcap else 'Unavailable'}")
            print(f"  pe_ratio:   {live.get('pe_ratio') or 'Unavailable'}")
            print(f"  sector:     {live.get('sector') or 'Unavailable'}")
        except Exception as exc:
            print(f"  ERROR: {exc}")


if __name__ == "__main__":
    main()
