"""
Sales Agent — monitors inbox for replies and responds with Calendly booking link.
No Calendly API needed — just sends the meeting link and lets leads self-book.
"""

import logging
from datetime import datetime

from tools.db_tools import update_lead_status, get_db
from tools.gmail_tools import check_for_replies, send_email, mark_as_read
from tools.llm_tools import classify_reply as llm_classify_reply
from templates.demo_pages import generate_demo, publish_demos
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
    "book a call", "schedule", "set up a call", "when are you",
    "available", "yes", "sure", "would love to", "open to", "curious",
    "how does", "what's the", "can you share", "send me", "demo",
]

_AUTO_REPLY_KEYWORDS = [
    "out of office", "auto-reply", "automatic reply", "away from",
    "vacation", "on leave", "will be back", "currently unavailable",
    "auto response",
]

_QUESTION_ANSWERS = {
    "price":     "Our pricing depends on the scope — most projects start around ₹50,000–₹2,00,000. Happy to give you a proper estimate on a quick call.",
    "cost":      "Our pricing depends on the scope — most projects start around ₹50,000–₹2,00,000. Happy to give you a proper estimate on a quick call.",
    "how long":  "Most projects take 2–6 weeks from kickoff to launch, depending on complexity.",
    "timeline":  "Most projects take 2–6 weeks from kickoff to launch, depending on complexity.",
    "portfolio": f"You can see recent projects here: {config.COMPANY_PORTFOLIO_URL}",
    "example":   f"You can see recent projects here: {config.COMPANY_PORTFOLIO_URL}",
}


def _classify_reply(text: str) -> tuple:
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
    for keyword, answer in _QUESTION_ANSWERS.items():
        if keyword in lower:
            return "question", answer
    if "?" in text:
        return "question", ""
    return "interested", ""


def _build_reply_html(first_name: str, company: str, demo_url: str, body_text: str) -> str:
    calendly = config.CALENDLY_MEETING_LINK
    return f"""
<html><body style="font-family: Arial, sans-serif; color: #333; max-width: 600px; margin: 0 auto;">
<p>Hi {first_name},</p>
{body_text}
<p>I put together a personalized demo for <strong>{company}</strong> so you can see exactly what we'd build:<br>
<a href="{demo_url}" style="color:#0066ff;font-weight:600;">View {company}'s Demo →</a></p>
<p>The easiest next step is a quick 30-minute call — you can pick a time that works for you right here:<br>
<a href="{calendly}" style="display:inline-block;margin-top:8px;padding:10px 20px;background:#0066ff;color:#fff;border-radius:6px;text-decoration:none;font-weight:600;">📅 Book a Free Call →</a></p>
<p>Looking forward to speaking with you!</p>
<p>Best,<br><strong>{config.SENDER_NAME}</strong><br>{config.COMPANY_NAME}<br>
<a href="{config.COMPANY_WEBSITE}" style="color:#0066ff;">{config.COMPANY_WEBSITE}</a></p>
</body></html>"""


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

        llm_result = llm_classify_reply(reply["snippet"], lead)
        if llm_result:
            intent = llm_result.get("intent", "question")
            draft_answer = llm_result.get("draft", "")
            logger.info(f"    → Intent (LLM): {intent}")
        else:
            intent, draft_answer = _classify_reply(reply["snippet"])
            logger.info(f"    → Intent (rule): {intent}")

        if intent == "auto_reply":
            mark_as_read(reply["message_id"])
            continue

        elif intent == "unsubscribe":
            if not dry_run:
                update_lead_status(lead["id"], "unsubscribed")
                mark_as_read(reply["message_id"])
            logger.info(f"    Unsubscribed: {from_email}")
            unsubscribes += 1

        elif intent == "not_interested":
            if not dry_run:
                update_lead_status(lead["id"], "not_interested",
                                   last_reply_at=datetime.utcnow().isoformat())
                mark_as_read(reply["message_id"])

        elif intent in ("interested", "question"):
            first_name = (lead["name"] or "").split()[0] or "there"
            demo_url = generate_demo(lead)

            if intent == "interested":
                body = "<p>Glad you're interested! Here's what I had in mind for you —</p>"
            else:
                extra = f"<p>{draft_answer}</p>" if draft_answer else ""
                body = f"<p>Great question!</p>{extra}"

            subject = f"Re: {reply['subject']}"
            html_body = _build_reply_html(first_name, lead["company"], demo_url, body)

            if not dry_run:
                publish_demos()
                send_email(
                    to_email=lead["email"],
                    to_name=lead["name"] or "",
                    subject=subject,
                    html_body=html_body,
                )
                update_lead_status(lead["id"], "replied",
                                   last_reply_at=datetime.utcnow().isoformat())
                mark_as_read(reply["message_id"])
                logger.info(f"    Sent reply + Calendly link to {from_email}")
            else:
                logger.info(f"    [DRY RUN] Would reply to {from_email} with demo + Calendly link")

            meetings_requested += 1

        processed += 1

    summary = {"replies_processed": processed, "meetings_requested": meetings_requested, "unsubscribes": unsubscribes}
    logger.info(f"Sales Agent done: {summary}")
    return summary


def sync_calendly_bookings(dry_run: bool = False) -> dict:
    """
    No Calendly API needed — leads self-book via the link in emails.
    This is a no-op kept for compatibility.
    """
    logger.info("Calendly sync skipped — using link-based booking (no API key required)")
    return {"meetings_synced": 0}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    import sys
    dry = "--dry-run" in sys.argv
    result = run_reply_monitor(dry_run=dry)
    print(f"\nSales Agent done: {result}")
