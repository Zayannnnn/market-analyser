import logging
import httpx
import asyncio
from typing import Dict, Any, Optional, List
from app.data_sources.market_data import upstox_client
from app.services.instrument_lookup import get_upstox_instrument

logger = logging.getLogger(__name__)

BASE_URL = "https://api.upstox.com/v2"

class UpstoxAPIError(Exception):
    """Custom exception class for Upstox API interaction errors."""
    def __init__(self, message: str, error_code: Optional[str] = None, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code

async def _execute_upstox_request(
    method: str,
    endpoint: str,
    json_data: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Helper method to execute authenticated HTTP calls to Upstox API with retries and timeout."""
    token = upstox_client.get_access_token()
    if not token:
        raise UpstoxAPIError("Broker authentication required. Access token missing.", error_code="AUTH_REQUIRED", status_code=401)

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    url = f"{BASE_URL}{endpoint}"

    # Perform request with retry logic (up to 3 attempts for transient issues or 429 Rate Limits)
    for attempt in range(1, 4):
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                if method == "GET":
                    response = await client.get(url, headers=headers, params=params)
                elif method == "POST":
                    response = await client.post(url, headers=headers, json=json_data)
                elif method == "PUT":
                    response = await client.put(url, headers=headers, json=json_data)
                elif method == "DELETE":
                    response = await client.delete(url, headers=headers, params=params)
                else:
                    raise UpstoxAPIError(f"Unsupported HTTP method: {method}", status_code=500)

                if response.status_code in [200, 201]:
                    payload = response.json()
                    if payload.get("status") == "success":
                        return payload.get("data") or {}
                    else:
                        errors = payload.get("errors", [{}])
                        err_msg = errors[0].get("message", "Upstox operation failed.")
                        err_code = errors[0].get("errorCode", "API_ERROR")
                        raise UpstoxAPIError(err_msg, error_code=err_code, status_code=400)

                elif response.status_code == 429:
                    logger.warning(f"Upstox rate limit encountered (attempt {attempt}/3). Retrying...")
                    await asyncio.sleep(1.0 * attempt)
                    continue

                elif response.status_code == 401:
                    raise UpstoxAPIError("Upstox session expired or token is invalid.", error_code="TOKEN_EXPIRED", status_code=401)

                else:
                    # Try to parse errors from standard JSON error payload
                    try:
                        err_json = response.json()
                        errors = err_json.get("errors", [{}])
                        err_msg = errors[0].get("message", f"HTTP {response.status_code}: {response.text}")
                        err_code = errors[0].get("errorCode", "API_ERROR")
                    except Exception:
                        err_msg = f"HTTP {response.status_code}: {response.text}"
                        err_code = "HTTP_ERROR"

                    raise UpstoxAPIError(err_msg, error_code=err_code, status_code=response.status_code)

        except httpx.RequestError as e:
            logger.warning(f"Connection or timeout error (attempt {attempt}/3): {e}")
            if attempt == 3:
                raise UpstoxAPIError(f"Upstox API Connection Failure: {e}", error_code="CONNECTION_ERROR", status_code=503)
            await asyncio.sleep(0.5 * attempt)

    raise UpstoxAPIError("Failed to complete request to Upstox API.", error_code="API_ERROR", status_code=500)

async def place_order(
    ticker: str,
    quantity: int,
    transaction_type: str,
    order_type: str,
    price: float = 0.0,
    product: str = "D"
) -> Dict[str, Any]:
    """Helper method to place standard Buy/Sell orders via Upstox API."""
    inst = get_upstox_instrument(ticker)
    if not inst:
        raise UpstoxAPIError(f"Symbol '{ticker}' not found in Upstox instruments index.", error_code="INSTRUMENT_NOT_FOUND")

    instrument_token = inst["instrument_key"]

    body = {
        "quantity": int(quantity),
        "product": product,
        "validity": "DAY",
        "price": float(price),
        "tag": "AORA",
        "instrument_token": instrument_token,
        "order_type": order_type,
        "transaction_type": transaction_type,
        "disclosed_quantity": 0,
        "trigger_price": 0.0,
        "is_amo": False
    }

    logger.info(f"Placing live order: {transaction_type} {quantity} {ticker} @ {price} ({order_type})")
    return await _execute_upstox_request("POST", "/order/place", json_data=body)

async def place_market_buy(ticker: str, quantity: int, product: str = "D") -> Dict[str, Any]:
    """Places a Market Buy order."""
    return await place_order(ticker, quantity, "BUY", "MARKET", price=0.0, product=product)

async def place_market_sell(ticker: str, quantity: int, product: str = "D") -> Dict[str, Any]:
    """Places a Market Sell order."""
    return await place_order(ticker, quantity, "SELL", "MARKET", price=0.0, product=product)

async def place_limit_buy(ticker: str, quantity: int, price: float, product: str = "D") -> Dict[str, Any]:
    """Places a Limit Buy order."""
    return await place_order(ticker, quantity, "BUY", "LIMIT", price=price, product=product)

async def place_limit_sell(ticker: str, quantity: int, price: float, product: str = "D") -> Dict[str, Any]:
    """Places a Limit Sell order."""
    return await place_order(ticker, quantity, "SELL", "LIMIT", price=price, product=product)

async def cancel_order(order_id: str) -> Dict[str, Any]:
    """Cancels a pending order."""
    params = {"order_id": order_id}
    logger.info(f"Cancelling Upstox order: {order_id}")
    return await _execute_upstox_request("DELETE", "/order/cancel", params=params)

async def modify_order(
    order_id: str,
    quantity: int,
    price: float,
    order_type: str = "LIMIT",
    validity: str = "DAY"
) -> Dict[str, Any]:
    """Modifies a pending order."""
    body = {
        "order_id": order_id,
        "quantity": int(quantity),
        "price": float(price),
        "order_type": order_type,
        "validity": validity,
        "disclosed_quantity": 0,
        "trigger_price": 0.0
    }
    logger.info(f"Modifying Upstox order {order_id}: qty={quantity}, price={price}")
    return await _execute_upstox_request("PUT", "/order/modify", json_data=body)

async def get_orders() -> List[Dict[str, Any]]:
    """Retrieves all orders in the current session (Order Book)."""
    res = await _execute_upstox_request("GET", "/order/book")
    return res if isinstance(res, list) else []

async def get_order_history(order_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieves execution history log events for session orders."""
    params = {}
    if order_id:
        params["order_id"] = order_id
    res = await _execute_upstox_request("GET", "/order/history", params=params)
    return res if isinstance(res, list) else []

async def get_positions() -> List[Dict[str, Any]]:
    """Retrieves current open and short-term holdings/positions."""
    res = await _execute_upstox_request("GET", "/portfolio/short-term-positions")
    return res if isinstance(res, list) else []
