import sys
import os

# Ensure the backend directory is in the Python search path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from firebase_functions import https_fn, scheduler_fn
from app.main import app as fastapi_app

# 1. Export FastAPI application as an HTTPS Cloud Function named 'app'
# This maps requests to the router while preserving the '/api' prefix
app = https_fn.on_request(fastapi_app)

# 2. Export Scheduler functions for native cron execution
@scheduler_fn.on_schedule(schedule="every 15 minutes")
def scheduled_pipeline(event: scheduler_fn.ScheduledEvent) -> None:
    """Runs the full multi-agent stock scorer pipeline every 15 minutes."""
    from app.scheduler import run_agent_pipeline_job
    print("Firebase Scheduler: Executing 15-minute stock scoring pipeline.")
    run_agent_pipeline_job()

@scheduler_fn.on_schedule(schedule="30 3 * * 0")
def scheduled_weekly_report(event: scheduler_fn.ScheduledEvent) -> None:
    """Sends the weekly accuracy and optimization report on Sunday at 09:00 IST (03:30 UTC)."""
    from app.agents.learning_agent import send_weekly_report
    print("Firebase Scheduler: Executing Sunday weekly Telegram report.")
    send_weekly_report()

@scheduler_fn.on_schedule(schedule="0 10 * * 1-5")
def scheduled_daily_report(event: scheduler_fn.ScheduledEvent) -> None:
    """Sends the daily close report on Mon-Fri at 15:30 IST (10:00 UTC)."""
    from app.agents.alert_agent import send_daily_close_report
    print("Firebase Scheduler: Executing Daily close Telegram report.")
    send_daily_close_report()
