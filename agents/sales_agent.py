"""
Sales Agent — monitors inbox for replies and books meetings.

Responsibilities:
  1. Poll Gmail inbox for replies from leads
  2. Classify reply intent using Claude (interested / not interested / question / unsubscribe)
  3. For interested leads: send meeting confirmation email with Calendly link
  4. For questions: draft a smart reply using Claude
  5. For unsubscribes: mark lead as unsubscribed
  6. Poll Calendly for new bookings and update lead status to 'meeting_booked'
"""

import logging
from datetime import datetime
import anthropic

from tools.db_tools import get_leads_by_status, update_lead_status, get_db
from tools.gmail_tools import check_for_replies, send_email, mark_as_read
from tools.calendly_tools import get_scheduled_events, get_event_invitees
from templates.emails import meeting_confirmation
from config import config

logger = logging.getLogger(__name__)
claude = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)


def _classify_reply(reply_text: str, lead_name: str) -> dict:
    """
    Use Claude to classify a reply and draft a response if needed.
    Returns {intent, draft_reply}.
    Intent: 'interested' | 'not_interested' | 'question' | 'unsubscribe' | 'auto_reply'
    """
    response = claude.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=400,
        messages=[{
            "role": "user",
            "content": f"""You are a sales assistant for CVS (a custom CRM & SaaS development company).

A lead replied to our cold email. Classify the intent and draft a response if needed.

Lead name: {lead_name}
Reply: "{reply_text}"

Respond in JSON:
{{
  "intent": "interested|not_interested|question|unsubscribe|auto_reply",
  "reasoning": "one sentence",
  "draft_reply": "your reply here (only for 'interested' or 'question' intents, else empty string)"
}}

For "interested": draft reply sends Calendly link {config.CALENDLY_MEETING_LINK}
For "question": answer the question about CVS services briefly and naturally
For others: empty draft_reply"""
        }],
    )

    import json
    try:
        return json.loads(response.content[0].text)
    except Exception:
        return {"intent": "question", "draft_reply": "", "reasoning": "parse error"}


def run_reply_monitor(dry_run: bool = False) -> dict:
    """
    Check inbox for replies from leads and respond intelligently.
    """
    replies = check_for_replies()
    logger.info(f"Sales Agent: found {len(replies)} unread emails")

    # Build email→lead mapping from DB for emailed leads
    conn = get_db()
    emailed_leads = conn.execute(
        "SELECT id, name, email, company FROM leads WHERE status IN ('emailed', 'replied')"
    ).fetchall()
    conn.close()
    email_to_lead = {row["email"].lower(): dict(row) for row in emailed_leads}

    processed = 0
    meetings_requested = 0
    unsubscribes = 0

    for reply in replies:
        from_email = reply["from_email"].lower()
        lead = email_to_lead.get(from_email)

        if not lead:
            # Not one of our leads, skip
            continue

        logger.info(f"  Reply from {from_email} ({lead['company']}) — snippet: {reply['snippet'][:80]}")

        classification = _classify_reply(reply["snippet"], lead["name"])
        intent = classification.get("intent", "question")
        draft = classification.get("draft_reply", "")

        logger.info(f"    Intent: {intent} — {classification.get('reasoning', '')}")

        if intent == "unsubscribe":
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
            logger.info(f"    Marked {from_email} as not interested")

        elif intent == "auto_reply":
            if not dry_run:
                mark_as_read(reply["message_id"])
            logger.info(f"    Auto-reply from {from_email}, skipping")

        elif intent in ("interested", "question"):
            first_name = (lead["name"] or "").split()[0] or "there"

            if intent == "interested":
                subject, html_body = meeting_confirmation(first_name, lead["company"])
            else:
                # Use Claude's draft reply for questions
                subject = f"Re: {reply['subject']}"
                html_body = f"""
<html><body style="font-family: Arial, sans-serif; color: #333; max-width: 600px;">
<p>Hi {first_name},</p>
<p>{draft}</p>
<p>If you'd like to chat further, here's my calendar:<br>
<a href="{config.CALENDLY_MEETING_LINK}" style="color: #4F46E5;">Book a 15-min call →</a></p>
<p>Best,<br><strong>{config.SENDER_NAME}</strong><br>{config.COMPANY_NAME}</p>
</body></html>
"""

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
                logger.info(f"    [DRY RUN] Would send meeting link to {from_email}")

            meetings_requested += 1

        processed += 1

    summary = {
        "replies_processed": processed,
        "meetings_requested": meetings_requested,
        "unsubscribes": unsubscribes,
    }
    logger.info(f"Sales Agent reply monitor done: {summary}")
    return summary


def sync_calendly_bookings(dry_run: bool = False) -> dict:
    """
    Check Calendly for new bookings and mark leads as 'meeting_booked'.
    """
    events = get_scheduled_events(count=50)
    booked = 0

    conn = get_db()
    for event in events:
        try:
            invitees = get_event_invitees(event["uuid"])
            for inv in invitees:
                row = conn.execute(
                    "SELECT id FROM leads WHERE LOWER(email) = LOWER(?)", (inv["email"],)
                ).fetchone()
                if row:
                    if not dry_run:
                        update_lead_status(
                            row["id"],
                            "meeting_booked",
                            meeting_booked_at=event["start_time"],
                        )
                    logger.info(f"  Meeting booked: {inv['email']} at {event['start_time']}")
                    booked += 1
        except Exception as e:
            logger.error(f"  Calendly sync error for event {event['uuid']}: {e}")

    conn.close()
    summary = {"meetings_synced": booked}
    logger.info(f"Calendly sync done: {summary}")
    return summary


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    import sys
    dry = "--dry-run" in sys.argv
    r1 = run_reply_monitor(dry_run=dry)
    r2 = sync_calendly_bookings(dry_run=dry)
    print(f"\nSales Agent done: replies={r1}, calendly={r2}")
