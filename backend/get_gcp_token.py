import os
import sys
from google.oauth2 import service_account
import google.auth.transport.requests

key_path = "backend/serviceAccountKey.json"

def get_token():
    if not os.path.exists(key_path):
        print(f"[!] Key file not found: {key_path}")
        sys.exit(1)
        
    credentials = service_account.Credentials.from_service_account_file(
        key_path,
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    
    # Request access token
    request = google.auth.transport.requests.Request()
    credentials.refresh(request)
    
    # Print only the token to stdout
    print(credentials.token)

if __name__ == "__main__":
    get_token()
