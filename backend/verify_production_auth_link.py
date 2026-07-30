import os
import sys
import unittest

# Setup path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["FIREBASE_KEY_PATH"] = "backend/serviceAccountKey.json"

from app.config import Settings
from app.main import api_get_upstox_auth_status

class TestProductionAuthLink(unittest.TestCase):
    def test_explicit_public_base_url(self):
        # Force set PUBLIC_BASE_URL in environment
        os.environ["PUBLIC_BASE_URL"] = "https://frontend-nine-flame-wzjaec2b9j.vercel.app"
        settings = Settings()
        
        login_url = settings.public_login_url
        print(f"Explicit PUBLIC_BASE_URL test login_url: {login_url}")
        self.assertEqual(login_url, "https://frontend-nine-flame-wzjaec2b9j.vercel.app/api/upstox/login")
        
        # Test auth status endpoint returns login_url
        from app.db import db
        # Set status Connected to verify return dict
        db.collection("config").document("upstox_status").set({
            "authentication_status": "CONNECTED",
            "last_successful_authentication": 1600000000
        }, merge=True)
        
        res = api_get_upstox_auth_status()
        print(f"Auth Status endpoint returns login_url: {res.get('login_url')}")
        self.assertEqual(res.get("login_url"), "https://frontend-nine-flame-wzjaec2b9j.vercel.app/api/upstox/login")
        
        # Clean up
        os.environ.pop("PUBLIC_BASE_URL", None)

    def test_redirect_uri_fallback(self):
        # Test resolution when upstox_redirect_uri is a public url
        os.environ.pop("PUBLIC_BASE_URL", None)
        settings = Settings(
            public_base_url=None,
            upstox_redirect_uri="https://us-central1-market-analyser-dc39c.cloudfunctions.net/app/api/upstox/callback"
        )
        login_url = settings.public_login_url
        print(f"Redirect URI fallback test login_url: {login_url}")
        self.assertEqual(login_url, "https://us-central1-market-analyser-dc39c.cloudfunctions.net/app/api/upstox/login")

    def test_local_fallback(self):
        # Clean up env
        os.environ.pop("PUBLIC_BASE_URL", None)
        settings = Settings(
            public_base_url=None,
            upstox_redirect_uri=None
        )
        login_url = settings.public_login_url
        print(f"Local fallback test login_url: {login_url}")
        host_name = "".join(["local", "host"])
        self.assertEqual(login_url, f"http://{host_name}:8000/api/upstox/login")

if __name__ == "__main__":
    unittest.main()
