"""
Cron-style scheduler for the CVS Lead Gen pipeline.
Runs automatically on a schedule without any external cron setup.

Schedule:
  08:00 — Scout: scrape new leads
  09:00 — Outreach: send personalized emails (business hours)
  12:00 — Sales: check replies + sync Calendly
  17:00 — Sales: end-of-day reply check
  Every 3 days — Follow-up emails

Run: python scheduler.py
Or deploy with: nohup python scheduler.py &
"""

import time
import schedule
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [scheduler] %(levelname)s — %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("data/scheduler.log"),
    ],
)
logger = logging.getLogger("scheduler")


def job_scout():
    logger.info("Running Scout Agent...")
    from agents.scout_agent import run_scout
    run_scout(max_per_query=30)


def job_outreach():
    logger.info("Running Outreach Agent...")
    from agents.outreach_agent import run_outreach
    run_outreach(batch_size=25)


def job_followups():
    logger.info("Running Follow-up emails...")
    from agents.outreach_agent import run_followups
    run_followups()


def job_sales():
    logger.info("Running Sales Agent...")
    from agents.sales_agent import run_reply_monitor, sync_calendly_bookings
    run_reply_monitor()
    sync_calendly_bookings()


def job_dashboard():
    from main import print_dashboard
    print_dashboard()


# ── Schedule ───────────────────────────────────────────────────
schedule.every().day.at("08:00").do(job_scout)
schedule.every().day.at("09:00").do(job_outreach)
schedule.every().day.at("12:00").do(job_sales)
schedule.every().day.at("17:00").do(job_sales)
schedule.every(3).days.do(job_followups)
schedule.every().day.at("18:00").do(job_dashboard)

logger.info("CVS Lead Gen Scheduler started.")
logger.info("Schedule: Scout@8am, Outreach@9am, Sales@12pm+5pm, Follow-ups every 3 days")

while True:
    schedule.run_pending()
    time.sleep(60)
