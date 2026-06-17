"""
Outreach Agent — personalizes and sends emails to new leads.

Responsibilities:
  1. Fetch 'new' leads with email addresses from DB
  2. Use Claude to generate a personalized opener + pain point for each lead
  3. Send the initial outreach email via Gmail
  4. Update lead status to 'emailed'
  5. Retry follow-ups for leads who haven't replied after 3 days
"""

import logging
import anthropic
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
claude = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)


def _personalize_opener(lead: dict) -> tuple[str, str]:
    """
    Use Claude to generate a personalized opening line and pain point.
    Returns (personalized_line, pain_point).
    """
    prompt = f"""You are a B2B sales copywriter for CVS, a company that builds custom CRMs and SaaS products.

Write a hyper-personalized cold email opener (1-2 sentences max) for this lead:
- Name: {lead['name']}
- Title: {lead['title']}
- Company: {lead['company']}
- Industry: {lead['industry']}
- Location: {lead['location']}
- Source: {lead['source']}

Also suggest a specific pain point (3-5 words, e.g. "scaling your CRM integrations") relevant to their role.

Respond in this exact JSON format:
{{
  "opener": "Your personalized opening line here.",
  "pain_point": "their specific pain point"
}}

Rules:
- The opener must NOT start with "I" or "We"
- Reference something specific about their role or company
- Sound human, not salesy
- No emojis"""

    response = claude.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )

    import json
    try:
        data = json.loads(response.content[0].text)
        return data["opener"], data["pain_point"]
    except Exception:
        return (
            f"Noticed {lead['company']} is doing some interesting work in the {lead['industry']} space.",
            "streamlining your CRM workflow",
        )


def run_outreach(batch_size: int = 20, dry_run: bool = False) -> dict:
    """
    Send initial outreach emails to new leads with email addresses.
    Returns summary dict.
    """
    leads = get_leads_by_status("new")
    # Only process leads that have emails
    leads = [l for l in leads if l.get("email")][:batch_size]

    sent = 0
    skipped = 0
    failed = 0

    logger.info(f"Outreach Agent: {len(leads)} new leads to contact")

    for lead in leads:
        try:
            first_name = (lead["name"] or "").split()[0] if lead.get("name") else "there"
            opener, pain_point = _personalize_opener(lead)

            subject, html_body = initial_outreach(
                first_name=first_name,
                company=lead["company"] or "your company",
                title=lead["title"] or "",
                pain_point=pain_point,
                personalized_line=opener,
            )

            if dry_run:
                logger.info(f"[DRY RUN] Would email {lead['email']} — Subject: {subject}")
                sent += 1
                continue

            msg_id = send_email(
                to_email=lead["email"],
                to_name=lead["name"] or "",
                subject=subject,
                html_body=html_body,
            )

            update_lead_status(
                lead["id"],
                "emailed",
                email_sent_at=datetime.utcnow().isoformat(),
            )
            log_email(lead["id"], msg_id, subject, html_body, "initial_outreach")
            logger.info(f"  Emailed {lead['email']} ({lead['company']}) — msg_id: {msg_id}")
            sent += 1

        except Exception as e:
            logger.error(f"  Failed to email {lead.get('email')}: {e}")
            failed += 1

    summary = {"sent": sent, "skipped": skipped, "failed": failed}
    logger.info(f"Outreach Agent complete: {summary}")
    return summary


def run_followups(dry_run: bool = False) -> dict:
    """
    Send follow-up emails to leads who haven't replied in 3 days.
    """
    leads = get_leads_awaiting_followup(days_since_email=3)
    sent = 0
    failed = 0

    logger.info(f"Follow-up Agent: {len(leads)} leads need follow-up")

    for lead in leads:
        try:
            first_name = (lead["name"] or "").split()[0] if lead.get("name") else "there"

            # Generate a different value prop angle for follow-up
            response = claude.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=100,
                messages=[{
                    "role": "user",
                    "content": f"Write 1 sentence (max 20 words) re-engaging {first_name} at {lead['company']} "
                               f"({lead['title']}) about custom CRM/SaaS development. Start with an insight, not 'I'."
                }],
            )
            value_prop = response.content[0].text.strip()

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
                lead["id"],
                "emailed",
                email_sent_at=datetime.utcnow().isoformat(),
                follow_up_count=lead["follow_up_count"] + 1,
            )
            log_email(lead["id"], msg_id, subject, html_body, "follow_up")
            logger.info(f"  Follow-up sent to {lead['email']}")
            sent += 1

        except Exception as e:
            logger.error(f"  Follow-up failed for {lead.get('email')}: {e}")
            failed += 1

    summary = {"sent": sent, "failed": failed}
    logger.info(f"Follow-up Agent complete: {summary}")
    return summary


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    import sys
    dry = "--dry-run" in sys.argv
    result = run_outreach(batch_size=10, dry_run=dry)
    print(f"\nOutreach done: {result}")
