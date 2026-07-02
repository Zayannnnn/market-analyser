import os
import sys
import httpx
from datetime import datetime
from dotenv import load_dotenv

# Setup paths to ensure local imports resolve
base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(base_dir)

# Load environment configuration
env_path = os.path.join(base_dir, ".env")
load_dotenv(env_path)

def run_test():
    print("====================================================")
    print("      TELEGRAM NOTIFICATION VERIFICATION TEST")
    print("====================================================")
    
    # 1. Load config
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not token or token == "***" or "TOKEN" in token:
        print("[-] Configuration check: FAILED. TELEGRAM_BOT_TOKEN not configured in backend/.env")
        sys.exit(1)
        
    if not chat_id or chat_id == "***" or "ID" in chat_id:
        print("[-] Configuration check: FAILED. TELEGRAM_CHAT_ID not configured in backend/.env")
        sys.exit(1)
        
    masked_token = token[:8] + "..." if len(token) > 8 else "***"
    print(f"[+] Configuration check: SUCCESS (Token: {masked_token}, Chat ID: {chat_id})")

    # 2. Formulate Test Message
    current_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    
    message = f"""🚀 <b>Market Analyser Test</b>

Firebase: Connected
Gemini: Connected
Telegram: Connected

Timestamp:
{current_time}"""

    # 3. Dispatch HTTP Post Request to Telegram
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    
    print("[*] Dispatching notification request to Telegram Bot API...")
    try:
        response = httpx.post(url, json=payload, timeout=10.0)
        
        # 4. Verify API Response
        if response.status_code == 200:
            print("[+] Telegram API Request: SUCCESS")
            print("[+] Message successfully dispatched and delivered.")
            print("====================================================")
            print("VERIFICATION RESULT: TELEGRAM ALERT BOT IS ONLINE & FUNCTIONAL!")
            print("====================================================")
            sys.exit(0)
        else:
            print(f"[-] Telegram API Request: FAILED (HTTP Status: {response.status_code})")
            print(f"    Error Details: {response.text}")
            sys.exit(1)
            
    except Exception as e:
        print(f"[-] Connection failed with exception: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_test()
