"""
Outreach Agent — personalizes and sends emails to new leads.
No AI API required — uses rule-based personalization from lead data.
"""

import logging
import random
from datetime import datetime

from tools.db_tools import (
    get_leads_by_status,
    update_lead_status,
    log_email,
    get_leads_awaiting_followup,
)
from tools.gmail_tools import send_email
from templates.emails import initial_outreach, follow_up
from config import config

logger = logging.getLogger(__name__)


# Openers keyed by lead source / title keywords
_OPENERS_BY_TITLE = [
    ("founder",    "Building a company from scratch means your tools need to work as hard as you do — most off-the-shelf CRMs just don't cut it at that stage."),
    ("cto",        "Engineering leaders at growing SaaS companies often tell us their biggest bottleneck isn't the product — it's the internal tooling holding the team back."),
    ("vp",         "Scaling a sales or ops team is hard enough without fighting a CRM that wasn't built for how your team actually works."),
    ("head",       "Teams at {company} stage often hit a wall where generic software stops fitting and custom builds start making sense."),
    ("director",   "At the director level, you probably feel the gap between what your current tools do and what your team actually needs."),
    ("manager",    "The best-run teams we work with all have one thing in common — their CRM fits their workflow, not the other way around."),
    ("owner",      "{company} caught our eye — businesses at your stage often find the biggest unlock is getting their customer data and workflow in one place."),
]

_OPENERS_DEFAULT = [
    "Came across {company} and thought what you're building in the {industry} space is exactly the kind of work we love helping scale.",
    "Teams like {company} are exactly who we built our CRM and SaaS development practice for.",
    "{company}'s growth in the {industry} space is impressive — wanted to reach out directly.",
]

_PAIN_POINTS_BY_INDUSTRY = {
    "saas":        "managing customer lifecycle at scale",
    "crm":         "replacing spreadsheets with a CRM that fits your sales motion",
    "software":    "cutting development time without cutting quality",
    "tech":        "building internal tools your team will actually use",
    "ecommerce":   "unifying your customer data across channels",
    "retail":      "connecting your POS and customer data in one place",
    "healthcare":  "managing patient workflows without expensive off-the-shelf software",
    "finance":     "automating your client reporting and onboarding workflows",
    "real estate": "tracking your pipeline from lead to close without juggling spreadsheets",
}

_PAIN_POINTS_DEFAULT = [
    "streamlining your CRM and client workflows",
    "reducing manual work across your sales and ops team",
    "building software that fits your process — not the other way around",
    "getting your customer data out of spreadsheets",
]

_FOLLOWUP_VALUE_PROPS = [
    "Companies at {company}'s stage typically save 10+ hours a week once their CRM fits their actual workflow.",
    "Most teams we work with see a 40% drop in manual data entry within the first month of going custom.",
    "A 15-minute call is often all it takes to figure out if a custom build makes sense for where {company} is headed.",
    "We recently helped a SaaS company very similar to {company} cut their CRM costs by 55% while shipping 3x faster.",
    "The difference between a CRM you bought and one built for you is usually about 6 weeks of dev time — worth a conversation.",
]


def _get_opener(lead: dict) -> str:
    title = (lead.get("title") or "").lower()
    company = lead.get("company") or "your company"
    industry = (lead.get("industry") or "").lower()

    for keyword, opener in _OPENERS_BY_TITLE:
        if keyword in title:
            return opener.format(company=company, industry=industry)

    return random.choice(_OPENERS_DEFAULT).format(company=company, industry=industry)


def _get_pain_point(lead: dict) -> str:
    industry = (lead.get("industry") or "").lower()
    for keyword, pain in _PAIN_POINTS_BY_INDUSTRY.items():
        if keyword in industry:
            return pain
    return random.choice(_PAIN_POINTS_DEFAULT)


def _get_followup_value_prop(lead: dict) -> str:
    company = lead.get("company") or "your company"
    return random.choice(_FOLLOWUP_VALUE_PROPS).format(company=company)


def run_outreach(batch_size: int = 20, dry_run: bool = False) -> dict:
    leads = get_leads_by_status("new")
    leads = [l for l in leads if l.get("email")][:batch_size]

    sent = skipped = failed = 0
    logger.info(f"Outreach Agent: {len(leads)} new leads to contact")

    for lead in leads:
        try:
            first_name = (lead["name"] or "").split()[0] if lead.get("name") else "there"
            opener = _get_opener(lead)
            pain_point = _get_pain_point(lead)

            subject, html_body = initial_outreach(
                first_name=first_name,
                company=lead["company"] or "your company",
                title=lead["title"] or "",
                pain_point=pain_point,
                personalized_line=opener,
            )

            if dry_run:
                logger.info(f"[DRY RUN] Would email {lead['email']} — Subject: {subject}")
                logger.info(f"           Opener: {opener}")
                sent += 1
                continue

            msg_id = send_email(
                to_email=lead["email"],
                to_name=lead["name"] or "",
                subject=subject,
                html_body=html_body,
            )

            update_lead_status(lead["id"], "emailed", email_sent_at=datetime.utcnow().isoformat())
            log_email(lead["id"], msg_id, subject, html_body, "initial_outreach")
            logger.info(f"  Emailed {lead['email']} ({lead['company']})")
            sent += 1

        except Exception as e:
            logger.error(f"  Failed to email {lead.get('email')}: {e}")
            failed += 1

    summary = {"sent": sent, "skipped": skipped, "failed": failed}
    logger.info(f"Outreach Agent complete: {summary}")
    return summary


def run_followups(dry_run: bool = False) -> dict:
    leads = get_leads_awaiting_followup(days_since_email=3)
    sent = failed = 0
    logger.info(f"Follow-up Agent: {len(leads)} leads need follow-up")

    for lead in leads:
        try:
            first_name = (lead["name"] or "").split()[0] if lead.get("name") else "there"
            value_prop = _get_followup_value_prop(lead)

            subject, html_body = follow_up(
                first_name=first_name,
                company=lead["company"] or "your company",
                original_subject=f"Quick question about {lead['company']}",
                value_prop=value_prop,
            )

            if dry_run:
                logger.info(f"[DRY RUN] Would follow up with {lead['email']}")
                sent += 1
                continue

            msg_id = send_email(
                to_email=lead["email"],
                to_name=lead["name"] or "",
                subject=subject,
                html_body=html_body,
            )

            update_lead_status(
                lead["id"], "emailed",
                email_sent_at=datetime.utcnow().isoformat(),
                follow_up_count=lead["follow_up_count"] + 1,
            )
            log_email(lead["id"], msg_id, subject, html_body, "follow_up")
            logger.info(f"  Follow-up sent to {lead['email']}")
            sent += 1

        except Exception as e:
            logger.error(f"  Follow-up failed for {lead.get('email')}: {e}")
            failed += 1

    return {"sent": sent, "failed": failed}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    import sys
    dry = "--dry-run" in sys.argv
    result = run_outreach(batch_size=10, dry_run=dry)
    print(f"\nOutreach done: {result}")
