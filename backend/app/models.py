from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class NewsArticle(BaseModel):
    id: str
    ticker: str
    title: str
    url: str
    source: str
    summary: str
    sentiment_score: Optional[float] = 0.0  # -100 to +100
    impact_level: Optional[str] = "low"     # low, medium, high
    published_at: str

class TechnicalIndicators(BaseModel):
    rsi: float
    macd: str
    sma50: float
    sma200: float
    volume_surge: float
    breakout_detected: bool

class AIExplanation(BaseModel):
    why_ranked: str
    bullish_factors: List[str]
    risk_factors: List[str]
    confidence_level: str  # Low, Medium, High

class Top10StockItem(BaseModel):
    rank: int
    ticker: str
    company_name: str
    price: str
    change: str
    score: int
    confidence: str
    sentiment: str
    recent_headline: str
    technical_indicators: TechnicalIndicators
    ai_explanation: AIExplanation
    subscores: Dict[str, float]

class Top10Response(BaseModel):
    timestamp: str
    market_summary: str
    top_10: List[Top10StockItem]

class IndexSummaryItem(BaseModel):
    price: float
    change: float
    history: List[float] = Field(default_factory=list)

class MarketSummaryResponse(BaseModel):
    timestamp: str
    sp500: IndexSummaryItem
    nasdaq: IndexSummaryItem
    nifty50: IndexSummaryItem
    sensex: IndexSummaryItem
    banknifty: IndexSummaryItem
    summary_text: str

class AlertModel(BaseModel):
    ticker: str
    company_name: str
    score: float
    confidence: str
    sentiment_score: float
    timestamp: str
    alert_sent: bool = True
