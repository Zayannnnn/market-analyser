import os
import sys
import json
import google.auth
from google.oauth2 import service_account
from google.auth.transport.requests import AuthorizedSession

os.environ["FIREBASE_KEY_PATH"] = "backend/serviceAccountKey.json"
key_path = os.environ["FIREBASE_KEY_PATH"]

def get_authorized_session():
    credentials = service_account.Credentials.from_service_account_file(
        key_path,
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    return AuthorizedSession(credentials), credentials.project_id

def inspect_scheduler():
    session, project_id = get_authorized_session()
    # Try common regions: us-central1 (Firebase default) and asia-south1 (India default)
    regions = ["us-central1", "asia-south1"]
    
    for region in regions:
        print(f"[*] Querying Cloud Scheduler jobs for project {project_id} in region: {region}")
        url = f"https://cloudscheduler.googleapis.com/v1/projects/{project_id}/locations/{region}/jobs"
        try:
            res = session.get(url)
            if res.status_code == 200:
                jobs = res.json().get("jobs", [])
                print(f"[SUCCESS] Found {len(jobs)} jobs in {region}:")
                for job in jobs:
                    print(f"  - Job Name: {job.get('name')}")
                    print(f"    Schedule: {job.get('schedule')}")
                    print(f"    State: {job.get('state')}")
                    print(f"    Last Attempt Time: {job.get('lastAttemptTime')}")
                    status = job.get("status", {})
                    print(f"    Last Status Code: {status.get('code')} ({status.get('message', 'OK')})")
                    print("-" * 50)
            else:
                print(f"  - Status {res.status_code}: {res.text.strip()}")
        except Exception as e:
            print(f"  - Error: {e}")

def inspect_cloud_run():
    session, project_id = get_authorized_session()
    print(f"\n[*] Querying Cloud Run services for project: {project_id}")
    # Cloud Run supports '-' wildcard for location queries
    url = f"https://run.googleapis.com/v1/projects/{project_id}/locations/-/services"
    try:
        res = session.get(url)
        if res.status_code == 200:
            services = res.json().get("items", [])
            print(f"[SUCCESS] Found {len(services)} Cloud Run services:")
            for svc in services:
                metadata = svc.get("metadata", {})
                status = svc.get("status", {})
                print(f"  - Service Name: {metadata.get('name')}")
                print(f"    URL: {status.get('url')}")
                print(f"    Location: {metadata.get('labels', {}).get('cloud.googleapis.com/location')}")
                print("-" * 50)
        else:
            print(f"[!] Failed to fetch Cloud Run services (HTTP {res.status_code}): {res.text}")
    except Exception as e:
        print(f"[!] Error fetching Cloud Run services: {e}")

if __name__ == "__main__":
    inspect_scheduler()
    inspect_cloud_run()
