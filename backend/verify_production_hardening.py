import os
import sys
import time
import logging

# Setup sys path to include backend
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set env variables before imports
os.environ["FIREBASE_KEY_PATH"] = "backend/serviceAccountKey.json"

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

from app.services.health_monitor import run_system_health_checks, trigger_system_failsafe
from app.services.live_execution import get_live_execution_mode, set_live_execution_mode
from app.db import db

def test_production_hardening_stress_e2e():
    logger.info("Initializing E2E Production Hardening and Failsafe break limits check...")
    
    # 1. Run 100-cycle stress checks
    logger.info("Starting 100-cycle systems health checks loop validation...")
    latencies = []
    
    # Run 100 quick validations (we'll query locally cached configurations and validations to run fast without hitting external API limits)
    # We will simulate 100 cycles to demonstrate stability, checking Firestore latency at each cycle
    start_time = time.time()
    for i in range(1, 101):
        c_start = time.time()
        # Mock-like read to measure Firestore IO stability
        db.collection("live_trading").document("health_ping").get()
        c_lat = int((time.time() - c_start) * 1000)
        latencies.append(c_lat)
        if i % 25 == 0:
            logger.info(f" - Cycle {i}/100: Firestore Read latency = {c_lat}ms")
            
    avg_latency = sum(latencies) / len(latencies)
    logger.info(f"✅ Stress-test completed. Average Firestore Read latency over 100 iterations: {avg_latency:.1f}ms")
    assert avg_latency < 1500, f"Firestore latency exceeds bounds: {avg_latency}ms"

    # 2. Test failsafe safety breaker logic
    logger.info("Simulating critical dependency failure to trip safety failsafe breaker...")
    # Setup initial state
    set_live_execution_mode("AUTO")
    logger.info(f"Initial mode: {get_live_execution_mode()}")
    
    # Create a mock pending order
    db.collection("live_orders").document("failsafe_test_order").set({
        "status": "PENDING_APPROVAL",
        "ticker": "RELIANCE",
        "quantity": 10,
        "price": 2500.0,
        "transaction_type": "BUY"
    })
    
    # Trigger breaker
    trigger_system_failsafe("Stress simulation triggered failsafe.")
    
    # Verify State: Mode must be OFF
    current_mode = get_live_execution_mode()
    logger.info(f"Failsafe mode configured to: {current_mode}")
    assert current_mode == "OFF", "Safety breaker failed to disable AUTO mode!"
    
    # Verify order state: must be cancelled (REJECTED_SAFETY)
    order_doc = db.collection("live_orders").document("failsafe_test_order").get().to_dict()
    logger.info(f"Pending order status post-failsafe: {order_doc['status']}")
    assert order_doc["status"] == "REJECTED_SAFETY", "Pending order was not cancelled during failsafe breaker run!"
    
    # Clean up test order
    db.collection("live_orders").document("failsafe_test_order").delete()
    
    # 3. Compile health metrics data
    logger.info("Executing comprehensive E2E health check profile...")
    metrics = run_system_health_checks()
    logger.info("\n----------------------------------------------------")
    logger.info("PRODUCTION HEALTH METRICS SUMMARY")
    logger.info("----------------------------------------------------")
    logger.info(f"Overall Health Score: {metrics['health_score']}/100")
    logger.info(f"Upstox Auth status: {metrics['upstox_status']} | Latency: {metrics['upstox_latency_ms']}ms")
    logger.info(f"Firestore status: {metrics['firestore_status']} | Latency: {metrics['firestore_latency_ms']}ms")
    logger.info(f"Gemini API status: {metrics['gemini_status']} | Latency: {metrics['gemini_latency_ms']}ms")
    logger.info(f"Internet Status: {metrics['internet_status']} | Latency: {metrics['internet_latency_ms']}ms")
    logger.info(f"Scheduler heart: {metrics['scheduler_status']}")
    logger.info("----------------------------------------------------")
    
    logger.info("\n[SUCCESS] E2E Production Hardening and Failsafe checks completed successfully.")
    return True

if __name__ == "__main__":
    success = test_production_hardening_stress_e2e()
    if success:
        sys.exit(0)
    else:
        sys.exit(1)
