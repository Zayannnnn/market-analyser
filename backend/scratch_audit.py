import yfinance as yf
import requests
import json

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
})

t = yf.Ticker("HCLTECH.NS", session=session)
try:
    print("market_cap:", t.fast_info.market_cap)
    print("currency:", t.fast_info.currency)
    print("last_price:", t.fast_info.last_price)
    print("trailingPE:", t.info.get("trailingPE"))
except Exception as e:
    print("Error:", e)
