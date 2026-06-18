"""
Sales Agent — monitors inbox for replies and books meetings.
No AI API required — uses keyword-based reply classification.
"""

import logging
from datetime import datetime

from tools.db_tools import update_lead_status, get_db
from tools.gmail_tools import check_for_replies, send_email, mark_as_read
from tools.calendly_tools import get_scheduled_events, get_event_invitees
from templates.emails import meeting_confirmation
from config import config

logger = logging.getLogger(__name__)

_UNSUBSCRIBE_KEYWORDS = [
    "unsubscribe", "remove me", "stop emailing", "don't contact",
    "do not contact", "not interested", "remove from list", "opt out",
    "take me off", "please remove",
]

_NOT_INTERESTED_KEYWORDS = [
    "not interested", "no thanks", "no thank you", "not a fit",
    "not relevant", "not for us", "we don't need", "already have",
    "using something else", "happy with what we have", "pass",
]

_INTERESTED_KEYWORDS = [
    "interested", "tell me more", "sounds good", "let's talk", "let's chat",
    "book a call", "schedule", "calendly", "set up a call", "when are you",
    "available", "yes", "sure", "would love to", "open to", "curious",
    "how does", "what's the", "can you share", "send me", "demo",
]

_AUTO_REPLY_KEYWORDS = [
    "out of office", "auto-reply", "automatic reply", "away from",
    "vacation", "on leave", "will be back", "currently unavailable",
    "auto response",
]

_QUESTION_ANSWERS = {
    "price":      f"Our pricing depends on the scope of the project — most custom CRM builds start around $3,000-$8,000. Happy to give you a proper estimate on a quick call: {config.CALENDLY_MEETING_LINK}",
    "cost":       f"Our pricing depends on the scope of the project — most custom CRM builds start around $3,000-$8,000. Happy to give you a proper estimate on a quick call: {config.CALENDLY_MEETING_LINK}",
    "how long":   f"Most projects take 4-8 weeks from kickoff to launch, depending on complexity. We'd nail down the timeline on a discovery call: {config.CALENDLY_MEETING_LINK}",
    "timeline":   f"Most projects take 4-8 weeks from kickoff to launch, depending on complexity. We'd nail down the timeline on a discovery call: {config.CALENDLY_MEETING_LINK}",
    "portfolio":  f"Absolutely — you can see recent projects here: {config.COMPANY_PORTFOLIO_URL}. Happy to walk you through relevant case studies on a call too.",
    "example":    f"You can see recent projects here: {config.COMPANY_PORTFOLIO_URL}. Happy to walk you through relevant case studies on a call too.",
    "work":       f"We specialize in custom CRMs and SaaS products — everything from sales pipelines to client portals to internal ops tools. See examples: {config.COMPANY_PORTFOLIO_URL}",
    "team":       "We're a small, senior team — every project is handled by experienced developers, no juniors or outsourcing.",
    "tech":       "We build primarily in React, Node.js, Python, and PostgreSQL — but we adapt to whatever stack makes sense for your project.",
    "stack":      "We build primarily in React, Node.js, Python, and PostgreSQL — but we adapt to whatever stack makes sense for your project.",
}


def _classify_reply(text: str) -> tuple[str, str]:
    """
    Classify reply intent using keyword matching.
    Returns (intent, draft_answer).
    Intent: 'interested' | 'not_interested' | 'question' | 'unsubscribe' | 'auto_reply'
    """
    lower = text.lower()

    for kw in _AUTO_REPLY_KEYWORDS:
        if kw in lower:
            return "auto_reply", ""

    for kw in _UNSUBSCRIBE_KEYWORDS:
        if kw in lower:
            return "unsubscribe", ""

    for kw in _NOT_INTERESTED_KEYWORDS:
        if kw in lower:
            return "not_interested", ""

    for kw in _INTERESTED_KEYWORDS:
        if kw in lower:
            return "interested", ""

    # Check for questions and return a canned answer
    for keyword, answer in _QUESTION_ANSWERS.items():
        if keyword in lower:
            return "question", answer

    # Default: treat as a question if it ends with ? otherwise interested
    if "?" in text:
        return "question", f"Great question! The best way to cover this properly is on a quick call — here's my calendar: {config.CALENDLY_MEETING_LINK}"

    return "interested", ""


def run_reply_monitor(dry_run: bool = False) -> dict:
    replies = check_for_replies()
    logger.info(f"Sales Agent: found {len(replies)} unread emails")

    conn = get_db()
    emailed_leads = conn.execute(
        "SELECT id, name, email, company FROM leads WHERE status IN ('emailed', 'replied')"
    ).fetchall()
    conn.close()
    email_to_lead = {row["email"].lower(): dict(row) for row in emailed_leads}

    processed = meetings_requested = unsubscribes = 0

    for reply in replies:
        from_email = reply["from_email"].lower()
        lead = email_to_lead.get(from_email)
        if not lead:
            continue

        logger.info(f"  Reply from {from_email} ({lead['company']}): {reply['snippet'][:80]}")

        intent, draft_answer = _classify_reply(reply["snippet"])
        logger.info(f"    → Intent: {intent}")

        if intent == "auto_reply":
            mark_as_read(reply["message_id"])

        elif intent == "unsubscribe":
            if not dry_run:
                update_lead_status(lead["id"], "unsubscribed")
                mark_as_read(reply["message_id"])
            logger.info(f"    Marked {from_email} as unsubscribed")
            unsubscribes += 1

        elif intent == "not_interested":
            if not dry_run:
                update_lead_status(lead["id"], "not_interested",
                                   last_reply_at=datetime.utcnow().isoformat())
                mark_as_read(reply["message_id"])

        elif intent in ("interested", "question"):
            first_name = (lead["name"] or "").split()[0] or "there"

            if intent == "interested":
                subject, html_body = meeting_confirmation(first_name, lead["company"])
            else:
                subject = f"Re: {reply['subject']}"
                html_body = f"""
<html><body style="font-family: Arial, sans-serif; color: #333; max-width: 600px;">
<p>Hi {first_name},</p>
<p>{draft_answer}</p>
<p>Best,<br><strong>{config.SENDER_NAME}</strong><br>{config.COMPANY_NAME}</p>
</body></html>"""

            if not dry_run:
                send_email(
                    to_email=lead["email"],
                    to_name=lead["name"] or "",
                    subject=subject,
                    html_body=html_body,
                )
                update_lead_status(lead["id"], "replied",
                                   last_reply_at=datetime.utcnow().isoformat())
                mark_as_read(reply["message_id"])
            else:
                logger.info(f"    [DRY RUN] Would send {intent} response to {from_email}")

            meetings_requested += 1

        processed += 1

    summary = {"replies_processed": processed, "meetings_requested": meetings_requested, "unsubscribes": unsubscribes}
    logger.info(f"Sales Agent done: {summary}")
    return summary


def sync_calendly_bookings(dry_run: bool = False) -> dict:
    events = get_scheduled_events(count=50)
    booked = 0
    conn = get_db()

    for event in events:
        try:
            for inv in get_event_invitees(event["uuid"]):
                row = conn.execute(
                    "SELECT id FROM leads WHERE LOWER(email) = LOWER(?)", (inv["email"],)
                ).fetchone()
                if row:
                    if not dry_run:
                        update_lead_status(row["id"], "meeting_booked",
                                           meeting_booked_at=event["start_time"])
                    logger.info(f"  Meeting booked: {inv['email']} at {event['start_time']}")
                    booked += 1
        except Exception as e:
            logger.error(f"  Calendly sync error: {e}")

    conn.close()
    return {"meetings_synced": booked}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    import sys
    dry = "--dry-run" in sys.argv
    r1 = run_reply_monitor(dry_run=dry)
    r2 = sync_calendly_bookings(dry_run=dry)
    print(f"\nSales Agent done: replies={r1}, calendly={r2}")
