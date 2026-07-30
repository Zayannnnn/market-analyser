import os
import sys
import time
import unittest
from unittest.mock import MagicMock, patch

# Setup paths
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["FIREBASE_KEY_PATH"] = "backend/serviceAccountKey.json"

from app.main import api_get_stock_research
from app.services.research_engine import run_stock_research
from app.db import db

class TestResearchEngine(unittest.TestCase):
    def setUp(self):
        self.doc_ref = db.collection("research").document("BEL")
        self.doc_snap = self.doc_ref.get()

    def tearDown(self):
        # Restore doc
        if self.doc_snap.exists:
            self.doc_ref.set(self.doc_snap.to_dict())
        else:
            self.doc_ref.delete()

    @patch("google.generativeai.GenerativeModel")
    def test_run_stock_research_success(self, mock_model_cls):
        print("\n[*] Testing run_stock_research successfully generates and caches data...")
        
        # Setup mock model response
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = """
{
  "ticker": "BEL",
  "company_name": "Bharat Electronics Limited",
  "fundamental_analysis": {
    "revenue_growth_yoy": 15.4,
    "profit_growth_yoy": 18.2,
    "roe": 22.5,
    "roce": 28.1,
    "debt_to_equity": 0.05,
    "operating_margin": 24.3,
    "net_margin": 18.5,
    "free_cash_flow_cr": 1200.0,
    "promoter_holding": 51.14,
    "fii_holding": 17.5,
    "dii_holding": 23.2,
    "pe_ratio": 38.5,
    "peg_ratio": 1.8,
    "pb_ratio": 8.2,
    "dividend_yield": 1.2,
    "fundamental_score": 85
  },
  "earnings_performance": {
    "latest_quarter": "Q4 FY26",
    "quarterly_revenue_cr": 4500.0,
    "quarterly_profit_cr": 850.0,
    "revenue_surprise_pct": 2.5,
    "earnings_surprise_pct": 4.1,
    "margin_expansion_bps": 120,
    "guidance": "Management expects double-digit growth.",
    "conf_call_sentiment": "Positive",
    "overall_earnings_view": "Positive"
  },
  "news_intelligence": [
    {
      "category": "Company",
      "headline": "BEL secures major order.",
      "importance": "HIGH",
      "sentiment": "BULLISH",
      "confidence": 95,
      "expected_duration": "LONG_TERM"
    }
  ],
  "catalyst_analysis": [
    {
      "type": "Contracts",
      "description": "Bidding for navy radar contracts.",
      "impact": "HIGH"
    }
  ],
  "fair_value_valuation": {
    "intrinsic_value": 465.0,
    "current_price": 420.0,
    "upside_pct": 10.7,
    "margin_of_safety": 10.7,
    "valuation_grade": "FAIR"
  },
  "investment_memo": {
    "business_summary": "Core operations lead in defence electronics.",
    "competitive_advantages": "Strong government backings, R&D lead.",
    "key_risks": "Defense budget dependences.",
    "growth_drivers": "Defense indigenization pushes.",
    "technical_view": "Support boundaries hold.",
    "macro_view": "Industry capex cycles remain strong.",
    "ai_recommendation": "BUY",
    "confidence_score": 88
  }
}
"""
        mock_model.generate_content.return_value = mock_response
        mock_model_cls.return_value = mock_model
        
        # Execute research generator
        res = run_stock_research("BEL")
        self.assertEqual(res["ticker"], "BEL")
        self.assertEqual(res["fundamental_analysis"]["fundamental_score"], 85)
        self.assertEqual(res["investment_memo"]["ai_recommendation"], "BUY")
        
        # Check Firestore cache exist
        cache_data = self.doc_ref.get().to_dict()
        self.assertEqual(cache_data["company_name"], "Bharat Electronics Limited")
        print("  - Firestore research document cached and retrieved successfully.")

    def test_api_stock_research_stale_cache(self):
        print("\n[*] Testing /api/stocks/{ticker}/research endpoint stale cache behavior...")
        # Write cached data that is fresh (1 minute old)
        now_ts = time.time()
        self.doc_ref.set({
            "ticker": "BEL",
            "company_name": "Bharat Electronics Limited Cached",
            "updated_at": now_ts - 60.0
        })
        
        # Call API
        res = api_get_stock_research("BEL", refresh=False)
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["research"]["company_name"], "Bharat Electronics Limited Cached")
        print("  - Returned fresh cached research data successfully.")

if __name__ == "__main__":
    unittest.main()
