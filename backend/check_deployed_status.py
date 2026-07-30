import httpx

url = "https://frontend-nine-flame-wzjaec2b9j.vercel.app/api/paper/scheduler/status"
try:
    print(f"[*] Checking status of deployed endpoint: {url}...")
    res = httpx.get(url, timeout=15.0)
    print(f"Response Code: {res.status_code}")
    print(f"Payload: {res.text}")
except Exception as e:
    print(f"Error checking status: {e}")
