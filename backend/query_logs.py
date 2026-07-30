import os
import sys
import json
import google.auth
from google.oauth2 import service_account
from google.auth.transport.requests import AuthorizedSession

os.environ["FIREBASE_KEY_PATH"] = "backend/serviceAccountKey.json"
key_path = os.environ["FIREBASE_KEY_PATH"]

def query_gcp_logs():
    credentials = service_account.Credentials.from_service_account_file(
        key_path,
        scopes=["https://www.googleapis.com/auth/logging.read", "https://www.googleapis.com/auth/cloud-platform"]
    )
    session = AuthorizedSession(credentials)
    project_id = credentials.project_id
    
    print(f"[*] Querying Cloud Logging for project: {project_id}")
    
    url = "https://logging.googleapis.com/v2/entries:list"
    
    # We query logs matching cloudscheduler or functions
    body = {
        "resourceNames": [f"projects/{project_id}"],
        "filter": 'resource.type="cloud_function" OR resource.type="cloud_scheduler_job" OR logName:"cloudaudit.googleapis.com"',
        "orderBy": "timestamp desc",
        "pageSize": 20
    }
    
    try:
        res = session.post(url, json=body)
        if res.status_code == 200:
            entries = res.json().get("entries", [])
            print(f"[SUCCESS] Found {len(entries)} log entries:")
            for entry in entries:
                payload = entry.get("textPayload") or entry.get("jsonPayload") or entry.get("protoPayload", {}).get("methodName")
                print(f"  - Timestamp: {entry.get('timestamp')}")
                print(f"    Resource: {entry.get('resource', {}).get('type')}")
                print(f"    Log: {payload}")
                print("-" * 50)
        else:
            print(f"[!] Failed to fetch logs (HTTP {res.status_code}): {res.text}")
    except Exception as e:
        print(f"[!] Error querying logs: {e}")

if __name__ == "__main__":
    query_gcp_logs()
