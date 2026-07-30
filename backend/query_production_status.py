import httpx

url = "https://frontend-nine-flame-wzjaec2b9j.vercel.app/api/upstox/auth-status"
try:
    print(f"[*] Sending GET to {url}...")
    res = httpx.get(url, timeout=30.0)
    print(f"URL: {url} -> HTTP {res.status_code}")
    print(f"Response: {res.text}")
except Exception as e:
    print(f"Error: {e}")
