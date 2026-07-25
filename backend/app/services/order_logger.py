import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional
from app.db import db

logger = logging.getLogger(__name__)

def log_order_attempt(
    ticker: str,
    side: str,
    quantity: int,
    price: float,
    order_type: str,
    ai_recommendation: str,
    confidence: int,
    execution_status: str,
    order_id: Optional[str] = None,
    broker_response: Optional[str] = None,
    error_code: Optional[str] = None
) -> str:
    """Logs an order execution attempt to Firestore under order_logs collection."""
    try:
        log_id = f"log_{int(time.time() * 1000)}"
        log_doc = {
            "log_id": log_id,
            "ticker": ticker.upper(),
            "side": side.upper(),
            "quantity": int(quantity),
            "price": float(price),
            "order_type": order_type.upper(),
            "ai_recommendation": ai_recommendation.upper(),
            "confidence": int(confidence),
            "execution_status": execution_status.upper(),
            "order_id": order_id,
            "broker_response": broker_response,
            "error_code": error_code,
            "timestamp": time.time(),
            "created_at": datetime.utcnow().isoformat() + "Z"
        }
        
        db.collection("order_logs").document(log_id).set(log_doc)
        logger.info(f"Successfully logged order attempt {log_id} for {ticker} status={execution_status}")
        return log_id
    except Exception as e:
        logger.error(f"Failed to log order attempt to Firestore: {e}", exc_info=True)
        return ""
