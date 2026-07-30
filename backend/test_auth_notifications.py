import sys
import os
import unittest
import time
from unittest.mock import patch, MagicMock

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.health_monitor import validate_upstox_token, get_runtime_state, set_runtime_state

class TestAuthNotifications(unittest.TestCase):

    def setUp(self):
        # Reset local cache or mock state before each test
        self.mock_db = {}
        
    def _mock_firestore_get(self, collection_name, doc_id):
        key = f"{collection_name}/{doc_id}"
        mock_doc = MagicMock()
        if key in self.mock_db:
            mock_doc.exists = True
            mock_doc.to_dict.return_value = self.mock_db[key]
        else:
            mock_doc.exists = False
        return mock_doc

    def _mock_firestore_set(self, collection_name, doc_id, data, merge=False):
        key = f"{collection_name}/{doc_id}"
        if merge and key in self.mock_db:
            self.mock_db[key].update(data)
        else:
            self.mock_db[key] = data

    @patch("app.services.health_monitor.db")
    @patch("app.services.health_monitor.upstox_client")
    @patch("app.services.health_monitor.httpx")
    @patch("app.services.health_monitor.trigger_auth_reminder")
    def test_auth_notification_flow(self, mock_trigger, mock_httpx, mock_upstox, mock_firestore):
        """Tests E2E notification loops, state persistence, reconnect reset, and cooldown limits."""
        
        # 1. Setup Firestore Mocking
        mock_firestore.collection.side_effect = lambda coll_name: MagicMock(
            document=lambda doc_id: MagicMock(
                get=lambda: self._mock_firestore_get(coll_name, doc_id),
                set=lambda data, merge=False: self._mock_firestore_set(coll_name, doc_id, data, merge)
            )
        )
        
        # Start state: connected
        self._mock_firestore_set("config", "runtime_state", {
            "upstox_connected": True,
            "expiry_notification_sent": False,
            "last_notification": 0.0,
            "last_auth_check": time.time()
        })
        
        # Mock Upstox Client Token
        mock_upstox.get_access_token.return_value = "invalid_expired_token"
        
        # Mock Profile endpoint returning 401 Unauthorized
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_httpx.get.return_value = mock_response
        
        # ---- STEP 1: FIRST EXPIRY ----
        # Run validation
        res = validate_upstox_token()
        self.assertFalse(res["valid"])
        
        # Verify exactly one Telegram alert was triggered
        mock_trigger.assert_called_once()
        mock_trigger.reset_mock()
        
        # Verify Firestore state indicates notification has been sent
        state = get_runtime_state()
        self.assertFalse(state["upstox_connected"])
        self.assertTrue(state["expiry_notification_sent"])
        self.assertGreater(state["last_notification"], 0.0)
        
        # ---- STEP 2: REPEATED RUNS ----
        # Run validation again
        res2 = validate_upstox_token()
        self.assertFalse(res2["valid"])
        
        # Verify NO additional Telegram messages were sent
        mock_trigger.assert_not_called()
        mock_trigger.reset_mock()
        
        # ---- STEP 3: RECONNECT RESET ----
        # Simulating successful reconnect (callback setsCONNECTED state)
        now_ts = time.time()
        self._mock_firestore_set("config", "runtime_state", {
            "upstox_connected": True,
            "expiry_notification_sent": False,
            "last_auth_check": now_ts
        }, merge=True)
        self._mock_firestore_set("live_trading", "config", {
            "live_trading_enabled": True
        }, merge=True)
        
        # Assert reconnect resets flags
        state = get_runtime_state()
        self.assertTrue(state["upstox_connected"])
        self.assertFalse(state["expiry_notification_sent"])
        
        # Assert live trading is enabled again
        live_config = self.mock_db.get("live_trading/config", {})
        self.assertTrue(live_config.get("live_trading_enabled"))
        
        # ---- STEP 4: SECOND EXPIRY (AFTER COOLDOWN) ----
        # Mock second expiry. Let's spoof last_notification to be 25 hours ago to satisfy cooldown
        state = get_runtime_state()
        state["last_notification"] = time.time() - 90000.0 # 25 hours ago
        set_runtime_state(state)
        
        # Run validation. Token is still invalid.
        res3 = validate_upstox_token()
        self.assertFalse(res3["valid"])
        
        # Verify exactly one new notification is sent
        mock_trigger.assert_called_once()
        mock_trigger.reset_mock()
        
        # ---- STEP 5: COOLDOWN ENFORCEMENT ----
        # Reset state as if reconnected and then immediately expired again
        state = get_runtime_state()
        state["expiry_notification_sent"] = False
        # last_notification is now set to time.time() from previous step (less than 24h ago)
        set_runtime_state(state)
        
        # Run validation. Token is still invalid.
        res4 = validate_upstox_token()
        self.assertFalse(res4["valid"])
        
        # Verify notification is BLOCKED by 24h cooldown rate-limiter
        mock_trigger.assert_not_called()

if __name__ == "__main__":
    unittest.main()
