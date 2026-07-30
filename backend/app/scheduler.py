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
        # Run token validation check first (Task 2 check every 15 minutes)
        try:
            from app.services.health_monitor import validate_upstox_token
            validate_upstox_token()
        except Exception as auth_err:
            logger.error(f"Error validating token in scheduled pipeline job: {auth_err}")

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

def run_live_and_paper_automation():
    """Wrapper to run both paper trading automation and real live auto trading/monitoring."""
    logger.info("Executing Live and Paper Automation background scheduler cycle...")
    # 1. Run paper trading automation (simulation)
    try:
        from app.services.paper_scheduler import run_paper_trade_automation
        run_paper_trade_automation()
    except Exception as e:
        logger.error(f"Error running scheduled paper trade automation: {e}")
        
    # 2. Run real live auto trading execution
    try:
        from app.services.live_execution import run_live_auto_trading
        run_live_auto_trading()
    except Exception as e:
        logger.error(f"Error running scheduled live auto trading: {e}")
        
    # 3. Run real live positions stop-loss / take-profit monitoring
    try:
        from app.services.live_execution import monitor_live_positions
        monitor_live_positions()
    except Exception as e:
        logger.error(f"Error running scheduled live positions monitoring: {e}")

def init_scheduler():
    """Initializes and runs APscheduler interval loops and cron events."""
    scheduler = BackgroundScheduler()
    
    # 1. Pipeline interval check (every 15 mins)
    scheduler.add_job(
        run_agent_pipeline_job,
        'interval',
        minutes=15,
        id='agent_pipeline_job',
        replace_existing=True
    )
    
    # 2. Sunday Weekly report (09:00 IST / 03:30 UTC)
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
    except Exception as e:
        logger.error(f"Failed to schedule weekly report job: {e}")
        
    # 3. Morning Health Check (08:45 IST / 03:15 UTC Mon-Fri)
    try:
        from app.services.paper_scheduler import run_health_checks
        scheduler.add_job(
            run_health_checks,
            'cron',
            day_of_week='mon-fri',
            hour=3,
            minute=15,
            id='morning_health_check_job',
            replace_existing=True
        )
        logger.info("Scheduled Morning Health Check at 08:45 IST.")
    except Exception as e:
        logger.error(f"Failed to schedule morning health checks job: {e}")
        
    # 4. Watchlist Scanner and AI recommendations (09:15 IST / 03:45 UTC Mon-Fri)
    try:
        from app.services.paper_scheduler import execute_watchlist_auto_scan
        scheduler.add_job(
            execute_watchlist_auto_scan,
            'cron',
            day_of_week='mon-fri',
            hour=3,
            minute=45,
            id='watchlist_scanner_job',
            replace_existing=True
        )
        logger.info("Scheduled Watchlist Auto-Scanner at 09:15 IST.")
    except Exception as e:
        logger.error(f"Failed to schedule watchlist scanner job: {e}")
        
    # 5. Live Market Scan & Target/SL Tracker (Every 30 mins during market hours Mon-Fri)
    # Mon-Fri between 09:15 and 15:30 IST (03:45 to 10:00 UTC)
    try:
        scheduler.add_job(
            run_live_and_paper_automation,
            'cron',
            day_of_week='mon-fri',
            hour='3-10',
            minute='15,45',
            id='live_market_tracker_job',
            replace_existing=True
        )
        logger.info("Scheduled Live Market Tracker (Live & Paper) every 30 minutes during market hours.")
    except Exception as e:
        logger.error(f"Failed to schedule market tracker job: {e}")
        
    # 6. End of Day Close report (15:30 IST / 10:00 UTC Mon-Fri)
    try:
        from app.services.paper_scheduler import run_end_of_day_report
        scheduler.add_job(
            run_end_of_day_report,
            'cron',
            day_of_week='mon-fri',
            hour=10,
            minute=0,
            id='end_of_day_report_job',
            replace_existing=True
        )
        logger.info("Scheduled End of Day Close report at 15:30 IST.")
    except Exception as e:
        logger.error(f"Failed to schedule EOD close report job: {e}")
        
    # 7. Evening AI Learning Report (20:00 IST / 14:30 UTC Mon-Fri)
    try:
        from app.services.paper_scheduler import run_evening_learning_report
        scheduler.add_job(
            run_evening_learning_report,
            'cron',
            day_of_week='mon-fri',
            hour=14,
            minute=30,
            id='evening_learning_report_job',
            replace_existing=True
        )
        logger.info("Scheduled Evening AI Learning report at 20:00 IST.")
    except Exception as e:
        logger.error(f"Failed to schedule AI learning report job: {e}")
        
    scheduler.start()
    logger.info("Background APscheduler started successfully.")
    return scheduler
