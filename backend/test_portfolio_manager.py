import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.risk_engine import get_risk_rules, validate_portfolio_risk_rules

class TestPortfolioManager(unittest.TestCase):

    def test_default_risk_rules(self):
        """Verifies that default risk rules are loaded correctly."""
        rules = get_risk_rules()
        self.assertIn("max_portfolio_exposure_pct", rules)
        self.assertIn("max_sector_exposure_pct", rules)
        self.assertIn("max_single_stock_exposure_pct", rules)
        self.assertEqual(rules.get("max_single_stock_exposure_pct"), 20.0)

    def test_validate_portfolio_risk_rules_success(self):
        """Tests that a safe order triggers no violations."""
        portfolio = {
            "cash_available": 100000.0,
            "holdings": [
                {"ticker": "INFY", "quantity": 10, "last_price": 1500.0, "sector": "Technology"}
            ]
        }
        violations = validate_portfolio_risk_rules(
            ticker="TCS",
            qty=5,
            price=3000.0, # Order value ₹15,000
            transaction_type="BUY",
            portfolio=portfolio
        )
        self.assertEqual(len(violations), 0)

    def test_validate_portfolio_risk_rules_exposure_cap(self):
        """Tests that exceeding single stock exposure cap triggers a violation."""
        portfolio = {
            "cash_available": 100000.0,
            "holdings": [
                {"ticker": "INFY", "quantity": 10, "last_price": 1500.0, "sector": "Technology"}
            ]
        }
        # Order value ₹45,000 on TCS. Total Portfolio: ₹115,000. 45k/115k = 39.1% (Exceeds 20% limit)
        violations = validate_portfolio_risk_rules(
            ticker="TCS",
            qty=15,
            price=3000.0,
            transaction_type="BUY",
            portfolio=portfolio
        )
        self.assertTrue(any("single-stock exposure limit breach" in v.lower() for v in violations))

    def test_validate_portfolio_risk_rules_insufficient_cash(self):
        """Tests that insufficient cash triggers a violation."""
        portfolio = {
            "cash_available": 5000.0,
            "holdings": []
        }
        violations = validate_portfolio_risk_rules(
            ticker="INFY",
            qty=10,
            price=1500.0, # ₹15,000 required
            transaction_type="BUY",
            portfolio=portfolio
        )
        self.assertTrue(any("insufficient buying power" in v.lower() for v in violations))

    @patch("google.generativeai.GenerativeModel")
    @patch("app.services.portfolio_analysis_engine.get_live_portfolio_data")
    @patch("app.services.portfolio_analysis_engine.get_market_data")
    def test_holdings_analysis_engine(self, mock_market, mock_portfolio, mock_genai):
        """Tests E2E holdings analysis engine run and output recommendations."""
        mock_portfolio.return_value = {
            "authenticated": True,
            "cash_available": 50000.0,
            "holdings": [
                {"ticker": "BEL", "quantity": 100, "last_price": 200.0, "sector": "Defence"}
            ]
        }
        mock_market.return_value = {
            "history_close": [200.0] * 30,
            "history_high": [205.0] * 30,
            "history_low": [198.0] * 30,
            "history_volume": [1000] * 30,
            "price": 200.0
        }
        
        # Mock Gemini Flash response
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = '{"decision": "BUY", "confidence": 85, "risk_score": 30, "expected_reward": "Target resistance ₹230", "reasoning": ["Solid tech indicators", "Strong support at ₹195", "Regime is positive"], "suggested_quantity": 50}'
        mock_model.generate_content.return_value = mock_response
        mock_genai.return_value = mock_model
        
        from app.services.portfolio_analysis_engine import generate_holdings_analysis
        import asyncio
        
        loop = asyncio.get_event_loop()
        res = loop.run_until_complete(generate_holdings_analysis())
        
        self.assertEqual(res.get("status"), "success")
        self.assertEqual(len(res.get("holdings")), 1)
        holding = res["holdings"][0]
        self.assertEqual(holding["ticker"], "BEL")
        self.assertEqual(holding["analysis"]["decision"], "BUY")

if __name__ == "__main__":
    unittest.main()
