import os
import sys
import google.auth
from google.oauth2 import service_account
from google.auth.transport.requests import AuthorizedSession

os.environ["FIREBASE_KEY_PATH"] = "backend/serviceAccountKey.json"
key_path = os.environ["FIREBASE_KEY_PATH"]

def grant_actas_permission():
    print("====================================================")
    print("GCP IAM PERMISSION ENABLER (ActAs / Service Account User)")
    print("====================================================")
    
    credentials = service_account.Credentials.from_service_account_file(
        key_path,
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    session = AuthorizedSession(credentials)
    project_id = credentials.project_id
    client_email = credentials.service_account_email
    
    # The target service account that we need iam.serviceAccounts.ActAs permission on
    target_sa = f"{project_id}@appspot.gserviceaccount.com"
    print(f"[*] Deployer service account (Member): {client_email}")
    print(f"[*] Target runtime service account: {target_sa}")
    
    # 1. Fetch current IAM policy for the target service account
    print("\n[*] Fetching current IAM policy for target service account...")
    url = f"https://iam.googleapis.com/v1/projects/{project_id}/serviceAccounts/{target_sa}:getIamPolicy"
    
    res = session.post(url)
    if res.status_code != 200:
        print(f"[!] Failed to get IAM policy (HTTP {res.status_code}): {res.text}")
        sys.exit(1)
        
    policy = res.json()
    print("[SUCCESS] Policy fetched.")
    
    # 2. Add roles/iam.serviceAccountUser binding for our deployer service account
    bindings = policy.get("bindings", [])
    
    # Find existing serviceAccountUser binding or create a new one
    sa_user_binding = None
    for b in bindings:
        if b.get("role") == "roles/iam.serviceAccountUser":
            sa_user_binding = b
            break
            
    member_str = f"serviceAccount:{client_email}"
    
    if sa_user_binding:
        if member_str not in sa_user_binding["members"]:
            sa_user_binding["members"].append(member_str)
            print(f"[*] Appending deployer to existing roles/iam.serviceAccountUser members list.")
        else:
            print(f"[!] Deployer already has roles/iam.serviceAccountUser role binding.")
    else:
        sa_user_binding = {
            "role": "roles/iam.serviceAccountUser",
            "members": [member_str]
        }
        bindings.append(sa_user_binding)
        print(f"[*] Created new roles/iam.serviceAccountUser binding with deployer as member.")
        
    policy["bindings"] = bindings
    
    # 3. Write back the updated IAM policy
    print("\n[*] Updating IAM policy with new bindings...")
    update_url = f"https://iam.googleapis.com/v1/projects/{project_id}/serviceAccounts/{target_sa}:setIamPolicy"
    
    # setIamPolicy expects a body with policy object
    update_body = {"policy": policy}
    
    res_update = session.post(update_url, json=update_body)
    if res_update.status_code == 200:
        print("[SUCCESS] IAM policy updated successfully!")
        print("          Deployer service account now has ActAs permissions.")
    else:
        print(f"[!] Failed to update IAM policy (HTTP {res_update.status_code}): {res_update.text}")
        print("\n[*] Attempting Project-level IAM modification instead...")
        # Fallback to project-level IAM update if service account-level is restricted
        grant_project_level_iam(session, project_id, client_email)

def grant_project_level_iam(session, project_id, client_email):
    # Fetch project-level IAM policy
    url = f"https://cloudresourcemanager.googleapis.com/v1/projects/{project_id}:getIamPolicy"
    res = session.post(url)
    if res.status_code != 200:
        print(f"[!] Failed to fetch Project IAM policy (HTTP {res.status_code}): {res.text}")
        sys.exit(1)
        
    policy = res.json()
    bindings = policy.get("bindings", [])
    
    sa_user_binding = None
    for b in bindings:
        if b.get("role") == "roles/iam.serviceAccountUser":
            sa_user_binding = b
            break
            
    member_str = f"serviceAccount:{client_email}"
    
    if sa_user_binding:
        if member_str not in sa_user_binding["members"]:
            sa_user_binding["members"].append(member_str)
        else:
            print("[!] Deployer already present in project-level serviceAccountUser list.")
            return
    else:
        sa_user_binding = {
            "role": "roles/iam.serviceAccountUser",
            "members": [member_str]
        }
        bindings.append(sa_user_binding)
        
    policy["bindings"] = bindings
    
    update_url = f"https://cloudresourcemanager.googleapis.com/v1/projects/{project_id}:setIamPolicy"
    res_update = session.post(update_url, json={"policy": policy})
    if res_update.status_code == 200:
        print("[SUCCESS] Project-level Service Account User role granted successfully!")
    else:
        print(f"[!] Failed to update Project IAM policy (HTTP {res_update.status_code}): {res_update.text}")

if __name__ == "__main__":
    grant_actas_permission()
