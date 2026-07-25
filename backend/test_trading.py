import os
import sys
import unittest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

# Adjust path to import backend app
base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(base_dir)

from app.main import app
from app.services.upstox_trading import UpstoxAPIError

class TestTradingBackend(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    @patch("app.services.ai_trade_review.generate_ai_trade_review", new_callable=AsyncMock)
    def test_trading_review_endpoint(self, mock_generate_review):
        # Setup mock review response
        mock_generate_review.return_value = {
            "confidence": 85,
            "recommendation": "BUY",
            "risk": "Low",
            "expected_reward": "Target resistance at ₹280.00",
            "suggested_quantity": 15,
            "reasons": ["Technical trend is bullish", "News sentiment is positive"],
            "warnings": ["Low cash volume warning"]
        }

        payload = {
            "ticker": "BEL",
            "quantity": 10,
            "side": "BUY",
            "price": 250.00,
            "order_type": "LIMIT"
        }

        res = self.client.post("/api/trading/review", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["confidence"], 85)
        self.assertEqual(data["recommendation"], "BUY")
        self.assertEqual(data["risk"], "Low")
        self.assertEqual(len(data["reasons"]), 2)
        mock_generate_review.assert_called_once_with(
            ticker="BEL",
            quantity=10,
            side="BUY",
            price=250.00,
            order_type="LIMIT"
        )

    @patch("app.services.portfolio_engine.validate_trade_constraints", new_callable=AsyncMock)
    @patch("app.services.upstox_trading.place_market_buy", new_callable=AsyncMock)
    @patch("app.services.order_logger.log_order_attempt")
    @patch("app.data_sources.market_data.get_market_data")
    def test_trading_buy_endpoint_success(self, mock_get_market, mock_log, mock_place_buy, mock_validate):
        # Mock dependencies
        mock_get_market.return_value = {"price": 245.50}
        mock_validate.return_value = []  # No safety violations
        mock_place_buy.return_value = {"order_id": "upstox_order_12345"}

        payload = {
            "ticker": "BEL",
            "quantity": 10,
            "product": "D"
        }

        res = self.client.post("/api/trading/buy", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["order_id"], "upstox_order_12345")
        
        mock_validate.assert_called_once_with("BEL", 10, 245.50, "BUY")
        mock_place_buy.assert_called_once_with("BEL", 10, product="D")
        mock_log.assert_called()

    @patch("app.services.portfolio_engine.validate_trade_constraints", new_callable=AsyncMock)
    @patch("app.services.order_logger.log_order_attempt")
    @patch("app.data_sources.market_data.get_market_data")
    def test_trading_buy_endpoint_rejected_safety(self, mock_get_market, mock_log, mock_validate):
        # Mock safety failure
        mock_get_market.return_value = {"price": 245.50}
        mock_validate.return_value = ["Insufficient funds.", "Market is closed."]

        payload = {
            "ticker": "BEL",
            "quantity": 10,
            "product": "D"
        }

        res = self.client.post("/api/trading/buy", json=payload)
        self.assertEqual(res.status_code, 400)
        self.assertIn("Safety Check Rejected", res.json()["detail"])
        mock_log.assert_called_once()

if __name__ == "__main__":
    unittest.main()
