import os
import sys
import google.auth
from google.oauth2 import service_account
from google.auth.transport.requests import AuthorizedSession

os.environ["FIREBASE_KEY_PATH"] = "backend/serviceAccountKey.json"
key_path = os.environ["FIREBASE_KEY_PATH"]

def query_logs():
    credentials = service_account.Credentials.from_service_account_file(
        key_path,
        scopes=["https://www.googleapis.com/auth/logging.read", "https://www.googleapis.com/auth/cloud-platform"]
    )
    session = AuthorizedSession(credentials)
    project_id = credentials.project_id
    
    print(f"[*] Querying logs for project: {project_id}")
    url = "https://logging.googleapis.com/v2/entries:list"
    
    # Simple query with minimal filters to avoid permission scopes checks that might fail
    body = {
        "resourceNames": [f"projects/{project_id}"],
        "filter": 'logName:"logs/cloudfunctions.googleapis.com%2Fcloud-functions" OR logName:"logs/cloudaudit.googleapis.com"',
        "orderBy": "timestamp desc",
        "pageSize": 10
    }
    
    try:
        res = session.post(url, json=body)
        print(f"Response Status: {res.status_code}")
        if res.status_code == 200:
            entries = res.json().get("entries", [])
            print(f"[SUCCESS] Retrieved {len(entries)} entries:")
            for entry in entries:
                print(f"  - [{entry.get('timestamp')}] {entry.get('textPayload') or entry.get('jsonPayload')}")
        else:
            print(f"Failed: {res.text}")
    except Exception as e:
        print(f"Error querying logs: {e}")

if __name__ == "__main__":
    query_logs()
