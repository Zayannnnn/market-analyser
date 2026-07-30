import httpx

urls = [
    "https://us-central1-market-analyser-dc39c.cloudfunctions.net/app/api/top10",
    "https://frontend-nine-flame-wzjaec2b9j.vercel.app/api/top10"
]

for url in urls:
    try:
        print(f"[*] Sending request to {url} (60s timeout for cold start)...")
        res = httpx.get(url, timeout=60.0)
        print(f"URL: {url} -> HTTP {res.status_code}")
        if res.status_code == 200:
            print(f"  Success! Sample: {res.text[:150]}")
        else:
            print(f"  Fail response (first 200 chars): {res.text[:200]}")
    except Exception as e:
        print(f"URL: {url} -> Error: {e}")
