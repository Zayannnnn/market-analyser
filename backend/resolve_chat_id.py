import os
import sys
import httpx
from dotenv import load_dotenv

# Resolve file paths
base_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(base_dir, ".env")
load_dotenv(env_path)

def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token or token == "***" or "TOKEN" in token:
        print("[-] Error: TELEGRAM_BOT_TOKEN is not configured in backend/.env")
        sys.exit(1)
        
    print("====================================================")
    print("      TELEGRAM CHAT ID RESOLUTION UTILITY")
    print("====================================================")
    print("[*] Contacting Telegram Bot API getUpdates...")
    
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    try:
        response = httpx.get(url, timeout=10.0)
        if response.status_code != 200:
            print(f"[-] Telegram API returned HTTP error: {response.status_code}")
            sys.exit(1)
            
        data = response.json()
        if not data.get("ok"):
            print(f"[-] Telegram API error: {data.get('description', 'Unknown error')}")
            sys.exit(1)
            
        results = data.get("result", [])
        if not results:
            print("[-] No updates found.")
            print("\n    INSTRUCTIONS:")
            print("    1. Open Telegram.")
            print("    2. Search for @TradeLabAlertBot or visit: https://t.me/TradeLabAlertBot")
            print("    3. Click 'Start' and send any text message (e.g. 'hello').")
            print("    4. Re-run this script to automatically capture your Chat ID.")
            print("====================================================")
            sys.exit(0)
            
        # Extract the latest message context
        latest_update = results[-1]
        msg = latest_update.get("message") or latest_update.get("channel_post")
        if not msg:
            print("[-] Error: Latest update payload does not contain a message structure.")
            sys.exit(1)
            
        chat = msg.get("chat", {})
        chat_id = chat.get("id")
        user_label = chat.get("username") or chat.get("first_name") or chat.get("title") or "User"
        
        if not chat_id:
            print("[-] Error: Could not resolve a numeric chat ID from the message payload.")
            sys.exit(1)
            
        print(f"[+] Chat source identified: '{user_label}' (Chat ID: {chat_id})")
        print("[*] Writing Chat ID to backend/.env...")
        
        # Read env lines
        with open(env_path, "r") as f:
            lines = f.readlines()
            
        # Update matching key
        new_lines = []
        key_found = False
        for line in lines:
            if line.startswith("TELEGRAM_CHAT_ID="):
                new_lines.append(f"TELEGRAM_CHAT_ID={chat_id}\n")
                key_found = True
            else:
                new_lines.append(line)
                
        if not key_found:
            new_lines.append(f"TELEGRAM_CHAT_ID={chat_id}\n")
            
        with open(env_path, "w") as f:
            f.writelines(new_lines)
            
        print("[+] backend/.env successfully updated!")
        print("====================================================")
        print(f"Resolved variables: TELEGRAM_CHAT_ID = {chat_id}")
        print("====================================================")
        sys.exit(0)
        
    except Exception as e:
        print(f"[-] Execution failed with exception: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
