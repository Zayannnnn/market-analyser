import os
import sys
import subprocess
from google.oauth2 import service_account
import google.auth.transport.requests

key_path = "backend/serviceAccountKey.json"

def deploy():
    print("====================================================")
    print("FIREBASE FUNCTIONS DEPLOYER (AUTO-AUTHENTICATED)")
    print("====================================================")
    
    if not os.path.exists(key_path):
        print(f"[!] Service account key file not found: {key_path}")
        sys.exit(1)
        
    print("[*] Generating OAuth2 access token from service account key...")
    try:
        credentials = service_account.Credentials.from_service_account_file(
            key_path,
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        request = google.auth.transport.requests.Request()
        credentials.refresh(request)
        token = credentials.token
        print("[SUCCESS] Access token generated successfully.")
    except Exception as e:
        print(f"[!] Failed to generate token: {e}")
        sys.exit(1)
        
    print("\n[*] Launching Firebase Functions deployment...")
    # Set FIREBASE_TOKEN to the generated access token
    env = os.environ.copy()
    env["FIREBASE_TOKEN"] = token
    
    # We execute npx firebase-tools deploy --only functions
    # Using shell=True for windows command execution compatibility
    cmd = "npx firebase-tools deploy --only functions"
    try:
        # Run subprocess and stream output live
        process = subprocess.Popen(
            cmd,
            shell=True,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                print(output.strip())
                
        rc = process.poll()
        if rc == 0:
            print("\n[SUCCESS] Cloud Functions deployed successfully!")
        else:
            print(f"\n[FAILURE] Deployment failed with exit code {rc}")
            sys.exit(rc)
            
    except Exception as e:
        print(f"[!] Error running deployment command: {e}")
        sys.exit(1)

if __name__ == "__main__":
    deploy()
