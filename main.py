"""
CVS Lead Generation Machine — Main Orchestrator

Runs all three agents in sequence or individually.

Usage:
  python main.py               # Run full pipeline
  python main.py scout         # Only scrape leads
  python main.py outreach      # Only send emails
  python main.py sales         # Only check replies + Calendly
  python main.py --dry-run     # Simulate without sending emails
  python main.py dashboard     # Print lead pipeline stats
"""

import sys
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s — %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("data/leadgen.log"),
    ],
)
logger = logging.getLogger("main")


def print_dashboard():
    from tools.db_tools import init_db, get_db
    init_db()
    conn = get_db()

    statuses = conn.execute(
        "SELECT status, COUNT(*) as count FROM leads GROUP BY status ORDER BY count DESC"
    ).fetchall()

    total = conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
    with_email = conn.execute("SELECT COUNT(*) FROM leads WHERE email != ''").fetchone()[0]
    emails_sent = conn.execute("SELECT COUNT(*) FROM emails").fetchone()[0]

    conn.close()

    print("\n" + "="*50)
    print("   CVS Lead Gen Dashboard")
    print("="*50)
    print(f"  Total Leads:      {total}")
    print(f"  With Email:       {with_email}")
    print(f"  Emails Sent:      {emails_sent}")
    print("-"*50)
    for row in statuses:
        bar = "█" * min(row["count"], 30)
        print(f"  {row['status']:20s} {row['count']:4d}  {bar}")
    print("="*50 + "\n")


def run_full_pipeline(dry_run: bool = False):
    logger.info("="*60)
    logger.info(f"CVS Lead Gen Pipeline starting — {datetime.utcnow().isoformat()}")
    logger.info("="*60)

    # Step 1: Scout — find new leads
    logger.info("\n[1/3] SCOUT AGENT — scraping leads...")
    from agents.scout_agent import run_scout
    scout_result = run_scout(max_per_query=30)
    logger.info(f"Scout result: {scout_result}")

    # Step 2: Outreach — send personalized emails
    logger.info("\n[2/3] OUTREACH AGENT — sending emails...")
    from agents.outreach_agent import run_outreach, run_followups
    outreach_result = run_outreach(batch_size=20, dry_run=dry_run)
    followup_result = run_followups(dry_run=dry_run)
    logger.info(f"Outreach result: {outreach_result}")
    logger.info(f"Follow-up result: {followup_result}")

    # Step 3: Sales — handle replies + sync meetings
    logger.info("\n[3/3] SALES AGENT — monitoring replies & meetings...")
    from agents.sales_agent import run_reply_monitor, sync_calendly_bookings
    sales_result = run_reply_monitor(dry_run=dry_run)
    calendly_result = sync_calendly_bookings(dry_run=dry_run)
    logger.info(f"Sales result: {sales_result}")
    logger.info(f"Calendly sync: {calendly_result}")

    logger.info("\nPipeline complete.")
    print_dashboard()


if __name__ == "__main__":
    args = sys.argv[1:]
    dry_run = "--dry-run" in args

    if "dashboard" in args:
        print_dashboard()
    elif "scout" in args:
        from agents.scout_agent import run_scout
        batch_offset = 0
        if "--batch-offset" in args:
            idx = args.index("--batch-offset")
            batch_offset = int(args[idx + 1])
        run_scout(batch_offset=batch_offset)
    elif "outreach" in args:
        from agents.outreach_agent import run_outreach, run_followups
        run_outreach(dry_run=dry_run)
        run_followups(dry_run=dry_run)
    elif "sales" in args:
        from agents.sales_agent import run_reply_monitor, sync_calendly_bookings
        run_reply_monitor(dry_run=dry_run)
        sync_calendly_bookings(dry_run=dry_run)
    else:
        run_full_pipeline(dry_run=dry_run)
