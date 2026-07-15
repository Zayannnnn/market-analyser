import sys
import os
import logging
from datetime import datetime

# Ensure the backend directory is in the Python search path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backend.main")

from firebase_functions import https_fn, scheduler_fn
from app.main import app as fastapi_app

# Centralized deployment version identifier to verify deployment success
DEPLOYMENT_VERSION = "2026-07-08-v3.1.0"
logger.info(f"Loading AORA Cloud Functions - Version: {DEPLOYMENT_VERSION}")

# Define the service account that the functions should execute as (prevents ActAs permission denial)
SVC_ACCOUNT = "firebase-adminsdk-fbsvc@market-analyser-dc39c.iam.gserviceaccount.com"

def log_scheduler_execution(step: str, status: str, details: str = ""):
    """Writes execution traces directly to Firestore to provide equivalent Cloud Logging evidence."""
    try:
        from app.db import db, MockFirestoreClient
        if not isinstance(db, MockFirestoreClient):
            db.collection("scheduler_execution_logs").add({
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "version": DEPLOYMENT_VERSION,
                "step": step,
                "status": status,
                "details": details
            })
    except Exception as e:
        logger.error(f"Failed to log scheduler execution to Firestore: {e}")

from a2wsgi import ASGIMiddleware
from flask import Response

wsgi_app = ASGIMiddleware(fastapi_app)

# 1. Export FastAPI application wrapped as an HTTPS Cloud Function named 'app'
# This maps requests to the router while preserving the '/api' prefix
@https_fn.on_request(service_account=SVC_ACCOUNT)
def app(request: https_fn.Request) -> https_fn.Response:
    status_captured = []
    headers_captured = []
    
    def start_response(status, headers, exc_info=None):
        status_captured.append(status)
        headers_captured.extend(headers)
        
    body_iter = wsgi_app(request.environ, start_response)
    try:
        body = b"".join(body_iter)
    finally:
        if hasattr(body_iter, "close"):
            body_iter.close()
            
    status_code = int(status_captured[0].split()[0])
    response = Response(body, status=status_code, headers=headers_captured)
    return response


# 2. Export Scheduler functions for native cron execution
@scheduler_fn.on_schedule(schedule="every 15 minutes", service_account=SVC_ACCOUNT)
def scheduled_pipeline(event: scheduler_fn.ScheduledEvent) -> None:
    """Runs token validation and the full multi-agent stock scorer pipeline every 15 minutes."""
    log_scheduler_execution("INIT_PIPELINE", "INFO", "Firebase Scheduler starting 15-minute pipeline.")
    
    from app.services.health_monitor import validate_upstox_token
    
    logger.info(f"[{DEPLOYMENT_VERSION}] Firebase Scheduler: INITIATING token validation...")
    log_scheduler_execution("INIT_VALIDATE_TOKEN", "INFO", "Initiating token validation check.")
    try:
        val_res = validate_upstox_token()
        logger.info(f"[{DEPLOYMENT_VERSION}] Firebase Scheduler: Token validation completed. Outcome: {val_res}")
        log_scheduler_execution("COMPLETED_VALIDATE_TOKEN", "SUCCESS" if val_res.get("valid") else "EXPIRED", str(val_res))
    except Exception as e:
        logger.error(f"[{DEPLOYMENT_VERSION}] Firebase Scheduler: Token validation encountered exception: {e}")
        log_scheduler_execution("COMPLETED_VALIDATE_TOKEN", "ERROR", str(e))
        
    from app.scheduler import run_agent_pipeline_job
    logger.info(f"[{DEPLOYMENT_VERSION}] Firebase Scheduler: INITIATING stock scoring pipeline...")
    log_scheduler_execution("INIT_PIPELINE_JOB", "INFO", "Initiating run_agent_pipeline_job.")
    try:
        run_agent_pipeline_job()
        logger.info(f"[{DEPLOYMENT_VERSION}] Firebase Scheduler: Stock scoring pipeline finished successfully.")
        log_scheduler_execution("COMPLETED_PIPELINE_JOB", "SUCCESS", "Stock scoring pipeline completed successfully.")
    except Exception as e:
        logger.error(f"[{DEPLOYMENT_VERSION}] Firebase Scheduler: Pipeline execution failed: {e}")
        log_scheduler_execution("COMPLETED_PIPELINE_JOB", "ERROR", str(e))

@scheduler_fn.on_schedule(schedule="30 3 * * 0", service_account=SVC_ACCOUNT)
def scheduled_weekly_report(event: scheduler_fn.ScheduledEvent) -> None:
    """Sends the weekly accuracy and optimization report on Sunday at 09:00 IST (03:30 UTC)."""
    from app.agents.learning_agent import send_weekly_report
    logger.info(f"[{DEPLOYMENT_VERSION}] Firebase Scheduler: Executing Sunday weekly Telegram report.")
    try:
        send_weekly_report()
    except Exception as e:
        logger.error(f"[{DEPLOYMENT_VERSION}] Weekly report execution failed: {e}")

@scheduler_fn.on_schedule(schedule="0 10 * * 1-5", service_account=SVC_ACCOUNT)
def scheduled_daily_report(event: scheduler_fn.ScheduledEvent) -> None:
    """Sends the daily close report on Mon-Fri at 15:30 IST (10:00 UTC)."""
    from app.agents.alert_agent import send_daily_close_report
    logger.info(f"[{DEPLOYMENT_VERSION}] Firebase Scheduler: Executing Daily close Telegram report.")
    try:
        send_daily_close_report()
    except Exception as e:
        logger.error(f"[{DEPLOYMENT_VERSION}] Daily close report execution failed: {e}")
