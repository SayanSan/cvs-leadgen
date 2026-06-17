"""
Calendly API wrapper — get meeting link, check scheduled events.
"""

import requests
from config import config

CALENDLY_BASE = "https://api.calendly.com"
HEADERS = {
    "Authorization": f"Bearer {config.CALENDLY_API_KEY}",
    "Content-Type": "application/json",
}


def get_meeting_link() -> str:
    """Return the configured Calendly scheduling link."""
    return config.CALENDLY_MEETING_LINK


def get_current_user() -> dict:
    r = requests.get(f"{CALENDLY_BASE}/users/me", headers=HEADERS)
    r.raise_for_status()
    return r.json()["resource"]


def get_scheduled_events(count: int = 20) -> list[dict]:
    """Fetch upcoming scheduled meetings from Calendly."""
    user = get_current_user()
    r = requests.get(
        f"{CALENDLY_BASE}/scheduled_events",
        headers=HEADERS,
        params={
            "user": user["uri"],
            "count": count,
            "status": "active",
            "sort": "start_time:asc",
        },
    )
    r.raise_for_status()
    events = r.json()["collection"]
    return [
        {
            "uuid": e["uri"].split("/")[-1],
            "name": e["name"],
            "start_time": e["start_time"],
            "end_time": e["end_time"],
            "status": e["status"],
            "invitees_url": e["uri"] + "/invitees",
        }
        for e in events
    ]


def get_event_invitees(event_uuid: str) -> list[dict]:
    """Get invitee details (name + email) for a scheduled event."""
    r = requests.get(
        f"{CALENDLY_BASE}/scheduled_events/{event_uuid}/invitees",
        headers=HEADERS,
    )
    r.raise_for_status()
    return [
        {
            "name": inv["name"],
            "email": inv["email"],
            "status": inv["status"],
            "created_at": inv["created_at"],
        }
        for inv in r.json()["collection"]
    ]
