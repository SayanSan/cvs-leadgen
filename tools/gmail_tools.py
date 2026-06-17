"""
Gmail API wrapper — send, read, and check for replies.
Setup: Enable Gmail API in Google Cloud Console, download credentials.json
Run once interactively: python tools/gmail_tools.py --auth
"""

import base64
import os
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from config import config

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
]


def _get_service():
    creds = None
    if os.path.exists(config.GMAIL_TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(config.GMAIL_TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                config.GMAIL_CREDENTIALS_FILE, SCOPES
            )
            creds = flow.run_local_server(port=0)
        with open(config.GMAIL_TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
    return build("gmail", "v1", credentials=creds)


def send_email(
    to_email: str,
    to_name: str,
    subject: str,
    html_body: str,
    plain_body: str = "",
) -> str:
    """Send an email and return the Gmail message ID."""
    service = _get_service()

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{config.SENDER_NAME} <{config.SENDER_EMAIL}>"
    msg["To"] = f"{to_name} <{to_email}>"

    if plain_body:
        msg.attach(MIMEText(plain_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    result = service.users().messages().send(userId="me", body={"raw": raw}).execute()
    return result["id"]


def check_for_replies(after_message_id: str = None) -> list[dict]:
    """
    Fetch unread replies in inbox.
    Returns list of {message_id, from_email, subject, snippet, thread_id}.
    """
    service = _get_service()
    query = "is:unread in:inbox"
    results = service.users().messages().list(userId="me", q=query, maxResults=50).execute()
    messages = results.get("messages", [])

    replies = []
    for msg_ref in messages:
        msg = service.users().messages().get(
            userId="me", id=msg_ref["id"], format="metadata",
            metadataHeaders=["From", "Subject", "To"]
        ).execute()
        headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
        replies.append({
            "message_id": msg["id"],
            "thread_id": msg["threadId"],
            "from_email": _extract_email(headers.get("From", "")),
            "from_name": _extract_name(headers.get("From", "")),
            "subject": headers.get("Subject", ""),
            "snippet": msg.get("snippet", ""),
        })
    return replies


def mark_as_read(message_id: str):
    service = _get_service()
    service.users().messages().modify(
        userId="me", id=message_id,
        body={"removeLabelIds": ["UNREAD"]}
    ).execute()


def _extract_email(from_header: str) -> str:
    if "<" in from_header:
        return from_header.split("<")[1].rstrip(">")
    return from_header.strip()


def _extract_name(from_header: str) -> str:
    if "<" in from_header:
        return from_header.split("<")[0].strip().strip('"')
    return ""


if __name__ == "__main__" and "--auth" in sys.argv:
    _get_service()
    print("Gmail authentication successful. Token saved.")
