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
from tools.llm_tools import personalize_email_opener, personalize_pain_point, draft_followup
from templates.emails import initial_outreach, follow_up
from templates.demo_pages import generate_demo, publish_demos
from config import config

logger = logging.getLogger(__name__)


# Openers keyed by lead source / title keywords
_OPENERS_BY_TITLE = [
    ("founder",    "Most businesses like {company} are still relying on word-of-mouth — a proper website can turn that into 24/7 lead generation."),
    ("owner",      "Came across {company} and noticed most businesses in your space are leaving a lot of leads on the table without a strong online presence."),
    ("proprietor", "{company} caught my eye — customers are searching online before they walk in, and a great website is often what converts them."),
    ("director",   "At your scale, {company} deserves a digital presence that actually brings in business — not just a page that exists."),
    ("manager",    "The best local businesses we work with all say the same thing — their website became their best salesperson."),
    ("head",       "We've helped several businesses in the {industry} space turn their website into a real growth channel."),
    ("cto",        "If {company} is ready to move beyond spreadsheets and manual processes, a custom web or mobile app can completely change the game."),
]

_OPENERS_DEFAULT = [
    "Came across {company} while researching businesses in the {industry} space — you're doing interesting work and I think we can help you get more visibility online.",
    "Businesses like {company} in the {industry} industry often have great products/services but struggle to get found online — that's exactly what we fix.",
    "{company} showed up in our research and we think there's a real opportunity to grow your customer base with the right digital strategy.",
]

_PAIN_POINTS_BY_INDUSTRY = {
    "restaurant":     "getting found on Google and turning online searches into table bookings",
    "cafe":           "building a loyal customer base online and driving repeat visits",
    "retail":         "bringing your store online and reaching customers beyond your locality",
    "clothing":       "showcasing your collection online and running digital campaigns that actually convert",
    "jewellery":      "building an online presence that reflects the quality of your products",
    "salon":          "getting discovered on Google Maps and booking appointments online",
    "beauty":         "attracting new clients through Instagram, Google, and a proper booking website",
    "gym":            "filling your membership slots with targeted digital ads and a conversion-focused website",
    "fitness":        "growing your client base with online booking and social media marketing",
    "clinic":         "helping patients find you online and book appointments without calling",
    "dentist":        "getting more patients through Google search and a professional website",
    "diagnostic":     "making it easy for patients to book tests online and find your services",
    "real estate":    "generating qualified property leads online without relying entirely on referrals",
    "interior":       "showcasing your portfolio online and attracting high-value clients through search",
    "ca ":            "building trust with potential clients through a professional website and content",
    "chartered":      "getting found by businesses looking for accounting services in your area",
    "lawyer":         "turning your expertise into a lead-generating website that builds client trust",
    "travel":         "booking more tours and packages through an online presence that sells 24/7",
    "event":          "attracting more corporate clients through a strong portfolio website",
    "wedding":        "getting discovered by couples on Google and Instagram when they're planning",
    "coaching":       "enrolling more students online and reducing dependence on walk-ins",
    "hotel":          "driving direct bookings and reducing dependence on OTA commissions",
    "ecommerce":      "scaling your online sales with better SEO, ads, and a faster website",
    "manufacturing":  "generating B2B leads online from buyers who are actively searching",
    "hardware":       "reaching contractors and builders online before your competitors do",
    "furniture":      "showcasing your catalogue online to reach customers across the city",
    "pharmacy":       "getting found online when customers search for medicines and health products nearby",
}

_PAIN_POINTS_DEFAULT = [
    "getting more customers through a strong online presence",
    "being found by the right people on Google when they're ready to buy",
    "turning your website into a real source of new business",
    "running digital marketing that actually brings in leads — not just likes",
]

_FOLLOWUP_VALUE_PROPS = [
    "Most businesses we work with see a 30-40% increase in enquiries within 60 days of launching a proper website.",
    "A well-built website pays for itself in 3-6 months — after that, every lead it generates is free.",
    "We recently helped a {company}-type business in your city go from zero online presence to 200+ monthly enquiries.",
    "The businesses growing fastest in your space all have one thing in common — they invested early in their digital presence.",
    "A 15-minute call is all it takes to figure out what's holding {company} back online and what a fix would cost.",
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
    demos_generated = 0
    logger.info(f"Outreach Agent: {len(leads)} new leads to contact")

    for lead in leads:
        try:
            first_name = (lead["name"] or "").split()[0] if lead.get("name") else "there"
            # Try LLM first, fall back to rule-based
            opener = personalize_email_opener(lead) or _get_opener(lead)
            pain_point = personalize_pain_point(lead) or _get_pain_point(lead)

            # Generate personalized demo page
            demo_url = generate_demo(lead)
            demos_generated += 1
            logger.info(f"  Demo generated for {lead['company']}: {demo_url}")

            subject, html_body = initial_outreach(
                first_name=first_name,
                company=lead["company"] or "your company",
                title=lead["title"] or "",
                pain_point=pain_point,
                personalized_line=opener,
                demo_url=demo_url,
            )

            if dry_run:
                logger.info(f"[DRY RUN] Would email {lead['email']} — Subject: {subject}")
                logger.info(f"           Demo: {demo_url}")
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

    # Push all newly generated demos to GitHub Pages in one batch commit
    if demos_generated > 0 and not dry_run:
        publish_demos()

    summary = {"sent": sent, "skipped": skipped, "failed": failed, "demos": demos_generated}
    logger.info(f"Outreach Agent complete: {summary}")
    return summary


def run_followups(dry_run: bool = False) -> dict:
    leads = get_leads_awaiting_followup(days_since_email=3)
    sent = failed = 0
    logger.info(f"Follow-up Agent: {len(leads)} leads need follow-up")

    for lead in leads:
        try:
            first_name = (lead["name"] or "").split()[0] if lead.get("name") else "there"
            value_prop = draft_followup(lead, lead.get("follow_up_count", 0)) or _get_followup_value_prop(lead)

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
