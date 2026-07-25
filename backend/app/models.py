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

# --- New Trading & AI Review Schemas ---

class TradeReviewRequest(BaseModel):
    ticker: str
    quantity: int
    side: str  # "BUY" or "SELL"
    price: Optional[float] = None
    order_type: Optional[str] = "MARKET"

class AITradeReviewResponse(BaseModel):
    confidence: int
    recommendation: str
    risk: str
    expected_reward: str
    suggested_quantity: int
    reasons: List[str]
    warnings: List[str]

class OrderPlacementRequest(BaseModel):
    ticker: str
    quantity: int
    product: Optional[str] = "D"

class LimitOrderPlacementRequest(BaseModel):
    ticker: str
    quantity: int
    price: float
    product: Optional[str] = "D"

class OrderCancellationRequest(BaseModel):
    order_id: str

class OrderModificationRequest(BaseModel):
    order_id: str
    quantity: int
    price: float
    order_type: Optional[str] = "LIMIT"
    validity: Optional[str] = "DAY"

class TradingActionResponse(BaseModel):
    status: str
    order_id: Optional[str] = None
    message: Optional[str] = None
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
