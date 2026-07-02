import logging
from datetime import datetime, timezone, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from app.agents.news_collector import collect_and_match_news
from app.agents.sentiment import process_sentiment_analysis
from app.agents.technical import run_technical_agent
from app.agents.ranking import run_ranking_agent
from app.agents.explanation import process_ai_explanations
from app.agents.alert_agent import run_alert_agent, send_daily_close_report
from app.agents.learning_agent import (
    track_predictions,
    evaluate_predictions,
    calculate_and_save_stats,
    optimize_weights,
    send_weekly_report
)

logger = logging.getLogger(__name__)

def run_agent_pipeline_job():
    """
    Executes the sequential workflow of all 7 agents:
    1. Collector -> 2. Sentiment -> 3. Technical -> 4. Scorer -> 5. Explanation -> 6. Alerts -> 7. Learning
    """
    logger.info("Executing background scheduler stock analysis pipeline.")
    try:
        # Agent 1: Scrape & Match news
        clean_news = collect_and_match_news()
        
        # Agent 2: Analyze sentiment of new articles
        process_sentiment_analysis(clean_news)
        
        # Agent 3: Update price streams and calculate indicators
        run_technical_agent()
        
        # Agent 4: Apply multi-criteria formula and update top 10 rankings
        top10 = run_ranking_agent()
        
        # Agent 5: Expose explanations & growth factors
        analyzed_top10 = process_ai_explanations(top10)
        
        # Agent 6: Scan opportunities and alert via Telegram
        run_alert_agent(analyzed_top10)
        
        # User-Specific Telegram alerts scanner
        try:
            logger.info("Scanning user-specific active target score alerts...")
            from app.agents.alert_agent import check_user_alerts
            check_user_alerts()
        except Exception as e:
            logger.error(f"Error checking user-defined alerts: {e}")
            
        # Agent 7: Learning Agent tracking & stats optimization
        try:
            logger.info("Learning Agent: Running prediction tracking, evaluations, aggregates, and weight optimizations.")
            track_predictions(analyzed_top10)
            evaluate_predictions()
            calculate_and_save_stats()
            optimize_weights()
        except Exception as e:
            logger.error(f"Error running Learning Agent operations: {e}")
            
        # Sunday Weekly Telegram Report Check (runs if current time is Sunday between 9:00 and 9:15 AM IST)
        # 9:00 AM IST is 3:30 AM UTC
        try:
            ist_now = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
            if ist_now.weekday() == 6 and ist_now.hour == 9 and 0 <= ist_now.minute < 15:
                logger.info("Sunday 9:00 IST window matched. Triggering weekly Telegram report.")
                send_weekly_report()
        except Exception as e:
            logger.error(f"Error checking/sending weekly Telegram report inside pipeline: {e}")
        
        logger.info("Background stock analysis pipeline executed successfully.")
        return analyzed_top10
    except Exception as e:
        logger.error(f"Error executing scheduled agent pipeline: {e}")
        return []

def init_scheduler():
    """Initializes and runs APscheduler interval loops (15 minutes)."""
    scheduler = BackgroundScheduler()
    # Add interval loop
    scheduler.add_job(
        run_agent_pipeline_job,
        'interval',
        minutes=15,
        id='agent_pipeline_job',
        replace_existing=True
    )
    # Add weekly cron loop on Sunday 9:00 AM IST (3:30 AM UTC)
    try:
        scheduler.add_job(
            send_weekly_report,
            'cron',
            day_of_week='sun',
            hour=3,
            minute=30,
            id='weekly_report_job',
            replace_existing=True
        )
        logger.info("Scheduled weekly Telegram report cron job for Sunday 9:00 IST (3:30 UTC).")
    except Exception as e:
        logger.error(f"Failed to schedule weekly report cron job: {e}")
        
    # Add daily close report cron job for Mon-Fri at 15:30 IST (10:00 UTC)
    try:
        scheduler.add_job(
            send_daily_close_report,
            'cron',
            day_of_week='mon-fri',
            hour=10,
            minute=0,
            id='daily_close_report_job',
            replace_existing=True
        )
        logger.info("Scheduled daily close report cron job for Mon-Fri 15:30 IST (10:00 UTC).")
    except Exception as e:
        logger.error(f"Failed to schedule daily close report cron job: {e}")
        
    scheduler.start()
    logger.info("Background APscheduler started. Stock pipeline running every 15 minutes.")
    return scheduler
