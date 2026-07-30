import httpx

urls = [
    "https://aora-backend-wzjaec2b9j-el.a.run.app/",
    "https://aora-backend-wzjaec2b9j-el.a.run.app/api/top10",
    "https://aora-backend-wzjaec2b9j-el.a.run.app/api/upstox/auth-status",
    "https://aora-backend-wzjaec2b9j-el.a.run.app/api/paper/scheduler/status"
]

for url in urls:
    try:
        res = httpx.get(url, timeout=10.0)
        print(f"URL: {url} -> HTTP {res.status_code}")
        print(f"  Response: {res.text[:150]}")
    except Exception as e:
        print(f"URL: {url} -> Error: {e}")
