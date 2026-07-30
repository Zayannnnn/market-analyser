import httpx

base_url = "https://frontend-nine-flame-wzjaec2b9j.vercel.app"

endpoints = [
    ("/api/top10", "GET"),
    ("/api/market-summary", "GET"),
    ("/api/watchlist/rank?tickers=BEL,RELIANCE", "GET"),
    ("/api/upstox/auth-status", "GET"),
    ("/api/stocks/BEL/research", "GET"),
    ("/api/paper/scheduler/status", "GET"),
    ("/api/paper/scheduler/health-checks", "POST"),
    ("/api/analyze-stocks", "POST")
]

print("====================================================")
print("PRODUCTION ENDPOINTS DEPLOYMENT STATUS AUDIT")
print("====================================================")

for path, method in endpoints:
    url = base_url + path
    try:
        if method == "GET":
            res = httpx.get(url, timeout=30.0)
        else:
            res = httpx.post(url, timeout=30.0)
        print(f"{method} {path} -> HTTP {res.status_code}")
        if res.status_code == 200:
            print(f"  Sample Output: {res.text[:120]}...")
        else:
            print(f"  Error Response: {res.text[:120]}...")
    except Exception as e:
        print(f"{method} {path} -> Error: {e}")
    print("-" * 50)
print("====================================================")
