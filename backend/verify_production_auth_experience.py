import os
import sys
import time
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

# Setup paths
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["FIREBASE_KEY_PATH"] = "backend/serviceAccountKey.json"

from app.config import settings
from app.main import api_get_upstox_auth_status, api_upstox_login, api_upstox_callback
from app.services.health_monitor import validate_upstox_token
from app.db import db

class TestProductionAuthExperience(unittest.TestCase):
    def setUp(self):
        # Cache current settings and Firestore state to restore later
        self.status_ref = db.collection("config").document("upstox_status")
        self.status_snap = self.status_ref.get()
        self.auth_ref = db.collection("config").document("upstox")
        self.auth_snap = self.auth_ref.get()
        self.live_trading_ref = db.collection("live_trading").document("config")
        self.live_trading_snap = self.live_trading_ref.get()

    def tearDown(self):
        # Restore Firestore states
        if self.status_snap.exists:
            self.status_ref.set(self.status_snap.to_dict())
        else:
            self.status_ref.delete()
            
        if self.auth_snap.exists:
            self.auth_ref.set(self.auth_snap.to_dict())
        else:
            self.auth_ref.delete()
            
        if self.live_trading_snap.exists:
            self.live_trading_ref.set(self.live_trading_snap.to_dict())
        else:
            self.live_trading_ref.delete()

    def test_auth_status_endpoint(self):
        print("\n[*] Testing /api/upstox/auth-status response parameters...")
        now_ts = time.time()
        self.status_ref.set({
            "authentication_status": "CONNECTED",
            "last_successful_authentication": now_ts,
            "last_authentication_time": now_ts,
            "last_health_check": now_ts
        })
        
        status = api_get_upstox_auth_status()
        self.assertEqual(status["authentication_status"], "CONNECTED")
        self.assertIsNotNone(status["token_age_seconds"])
        self.assertIsNotNone(status["expected_expiry"])
        self.assertIn("expected_expiry_str", status)
        self.assertIn("live_trading_status", status)
        self.assertIn("last_health_check_str", status)
        print("  - Connection Status returned correctly.")
        print(f"  - Expected Expiry date string: {status['expected_expiry_str']}")

    @patch("app.services.health_monitor.validate_upstox_token")
    def test_login_flow_already_connected(self, mock_validate):
        print("\n[*] Testing /api/upstox/login when already connected...")
        # Mock token is valid
        mock_validate.return_value = {"valid": True, "reason": "Verified"}
        
        # Set database values
        now_ts = time.time()
        self.status_ref.set({
            "authentication_status": "CONNECTED",
            "last_successful_authentication": now_ts,
            "last_authentication_time": now_ts
        })
        
        from fastapi.responses import RedirectResponse
        res = api_upstox_login(force=False)
        self.assertIsInstance(res, RedirectResponse)
        self.assertEqual(res.headers.get("location"), settings.resolved_dashboard_url)
        print("  - Prevented redundant redirects successfully and redirected to dashboard.")

    @patch("app.services.health_monitor.validate_upstox_token")
    def test_login_flow_forced_or_invalid(self, mock_validate):
        print("\n[*] Testing /api/upstox/login when forced or expired...")
        # Mock token is invalid
        mock_validate.return_value = {"valid": False, "reason": "Expired"}
        
        from fastapi.responses import RedirectResponse
        res = api_upstox_login(force=True)
        self.assertIsInstance(res, RedirectResponse)
        print("  - Correctly generated OAuth redirect URL.")

    @patch("httpx.post")
    @patch("httpx.get")
    def test_callback_verification_pipeline(self, mock_get, mock_post):
        print("\n[*] Testing callback validation checks & Telegram dispatcher...")
        
        # 1. Mock token exchange response
        mock_token_resp = MagicMock()
        mock_token_resp.status_code = 200
        mock_token_resp.json.return_value = {"access_token": "mocked_access_token_123"}
        mock_post.return_value = mock_token_resp
        
        # 2. Mock profile, holdings, and funds check
        mock_profile_resp = MagicMock()
        mock_profile_resp.status_code = 200
        mock_get.return_value = mock_profile_resp
        
        # Execute callback
        html_resp = api_upstox_callback(code="mock_code_abc")
        self.assertIsNotNone(html_resp)
        
        # Verify status document in Firestore
        status_data = self.status_ref.get().to_dict()
        self.assertEqual(status_data["authentication_status"], "CONNECTED")
        self.assertEqual(status_data["last_health_check_status"], "CONNECTED")
        print("  - Firestore token storage and authentication timestamps recorded.")

    @patch("httpx.get")
    def test_health_monitor_validation_success(self, mock_get):
        print("\n[*] Testing health_monitor.validate_upstox_token() success...")
        # Mock active token exists and profile returns 200
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp
        
        from app.data_sources.market_data import upstox_client
        with patch.object(upstox_client, 'get_access_token', return_value="some_token"):
            val_res = validate_upstox_token()
            self.assertTrue(val_res["valid"])
            
            # Check Firestore status document is updated to CONNECTED
            status_data = self.status_ref.get().to_dict()
            self.assertEqual(status_data["authentication_status"], "CONNECTED")
            print("  - Scheduler 15-minute verification updates Firestore metrics correctly.")

    @patch("httpx.get")
    def test_health_monitor_validation_expired(self, mock_get):
        print("\n[*] Testing health_monitor.validate_upstox_token() failure & live trading breaker...")
        # Mock active token exists but profile returns 401
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.text = "Unauthorized Token"
        mock_get.return_value = mock_resp
        
        from app.data_sources.market_data import upstox_client
        with patch.object(upstox_client, 'get_access_token', return_value="some_token"):
            val_res = validate_upstox_token()
            self.assertFalse(val_res["valid"])
            
            # Check live trading is disabled
            from app.services.live_execution import is_live_trading_enabled
            self.assertFalse(is_live_trading_enabled())
            
            # Check Firestore status document is updated to EXPIRED
            status_data = self.status_ref.get().to_dict()
            self.assertEqual(status_data["authentication_status"], "EXPIRED")
            print("  - Live trading paused automatically on expired session.")

if __name__ == "__main__":
    unittest.main()
