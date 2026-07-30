import os
import sys
import logging

# Setup sys path to include backend
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set env variables before imports
os.environ["FIREBASE_KEY_PATH"] = "backend/serviceAccountKey.json"

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

from app.services.live_execution import (
    place_live_order,
    approve_live_order,
    reject_live_order,
    is_live_trading_enabled,
    check_upstox_authentication,
    get_live_execution_mode,
    set_live_execution_mode
)
from app.db import db

def test_live_execution_e2e():
    logger.info("Initializing E2E Live Execution and Safety checks...")
    
    # 1. Security check: Real trading MUST remain disabled by default
    live_enabled = is_live_trading_enabled()
    logger.info(f"Is Live Cash Trading enabled: {live_enabled}")
    assert live_enabled is False, "SECURITY FAILURE: Real live trading is enabled by default!"
    logger.info("✅ Security boundary verified: Live cash trading is disabled by default.")
    
    # 2. Check Execution Mode default
    mode = get_live_execution_mode()
    logger.info(f"Default Execution Mode: {mode}")
    # Force set to CONFIRM to test manual approval workflow
    set_live_execution_mode("CONFIRM")
    logger.info("✅ Configured Mode to CONFIRM for testing.")
    
    # 3. Test Order Placement in CONFIRM mode
    logger.info("Placing a test order in CONFIRM mode...")
    order = place_live_order(
        ticker="BEL",
        qty=50,
        price=320.0,
        order_type="LIMIT",
        transaction_type="BUY",
        reason="E2E manual approval safety test"
    )
    
    order_id = order["order_id"]
    logger.info(f"Test order created. Order ID: {order_id} | Status: {order['status']} | Mode: {order['mode']}")
    assert order["status"] == "PENDING_APPROVAL", "Order should be PENDING_APPROVAL in CONFIRM mode."
    logger.info("✅ Placed order successfully (Pending Approval state confirmed).")
    
    # 4. Test Manual Approval workflow
    logger.info(f"Approving order {order_id} manually...")
    approved = approve_live_order(order_id)
    assert approved is True, "Manual approval trigger failed."
    
    # Reload from database to verify status updates
    updated_order = db.collection("live_orders").document(order_id).get().to_dict()
    logger.info(f"Updated order status: {updated_order['status']}")
    logger.info(f"Broker Response: {updated_order.get('broker_response')}")
    
    # Since live_trading_enabled is False, it should complete as FILLED_SIMULATED or exit on Safety violations
    assert updated_order["status"] in ["FILLED_SIMULATED", "REJECTED_SAFETY"], "Unexpected post-approval order status."
    logger.info("✅ Manual approval workflow successfully evaluated.")
    
    # 5. Place another order to test Rejection
    logger.info("Placing second test order to verify Rejection...")
    rej_order = place_live_order(
        ticker="TCS",
        qty=10,
        price=3800.0,
        order_type="LIMIT",
        transaction_type="BUY",
        reason="E2E rejection test"
    )
    rej_id = rej_order["order_id"]
    logger.info(f"Rejecting order {rej_id} manually...")
    rejected = reject_live_order(rej_id)
    assert rejected is True, "Manual rejection trigger failed."
    
    rej_updated = db.collection("live_orders").document(rej_id).get().to_dict()
    logger.info(f"Rejected order status: {rej_updated['status']}")
    assert rej_updated["status"] == "REJECTED_MANUAL", "Status should be REJECTED_MANUAL."
    logger.info("✅ Manual rejection workflow successfully evaluated.")
    
    logger.info("\n[SUCCESS] E2E Live Execution and Trade Safety verification completed successfully.")
    return True

if __name__ == "__main__":
    success = test_live_execution_e2e()
    if success:
        sys.exit(0)
    else:
        sys.exit(1)
