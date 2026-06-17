import sqlite3
import json
from datetime import datetime
from config import config


def get_db():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT UNIQUE,
            company TEXT,
            title TEXT,
            linkedin_url TEXT,
            source TEXT,
            industry TEXT,
            company_size TEXT,
            location TEXT,
            phone TEXT,
            website TEXT,
            status TEXT DEFAULT 'new',
            -- new | emailed | replied | meeting_booked | closed | unsubscribed
            email_sent_at TEXT,
            last_reply_at TEXT,
            meeting_booked_at TEXT,
            follow_up_count INTEGER DEFAULT 0,
            notes TEXT,
            raw_data TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id INTEGER REFERENCES leads(id),
            gmail_message_id TEXT,
            subject TEXT,
            body TEXT,
            template_type TEXT,
            sent_at TEXT DEFAULT (datetime('now')),
            opened INTEGER DEFAULT 0,
            replied INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()


def upsert_lead(lead: dict) -> int:
    conn = get_db()
    cur = conn.execute(
        """
        INSERT INTO leads (name, email, company, title, linkedin_url, source,
            industry, company_size, location, phone, website, raw_data)
        VALUES (:name, :email, :company, :title, :linkedin_url, :source,
            :industry, :company_size, :location, :phone, :website, :raw_data)
        ON CONFLICT(email) DO UPDATE SET
            name = excluded.name,
            company = excluded.company,
            title = excluded.title,
            linkedin_url = excluded.linkedin_url,
            industry = excluded.industry,
            company_size = excluded.company_size,
            location = excluded.location
        """,
        {
            "name": lead.get("name", ""),
            "email": lead.get("email", ""),
            "company": lead.get("company", ""),
            "title": lead.get("title", ""),
            "linkedin_url": lead.get("linkedin_url", ""),
            "source": lead.get("source", ""),
            "industry": lead.get("industry", ""),
            "company_size": lead.get("company_size", ""),
            "location": lead.get("location", ""),
            "phone": lead.get("phone", ""),
            "website": lead.get("website", ""),
            "raw_data": json.dumps(lead),
        },
    )
    conn.commit()
    lead_id = cur.lastrowid
    conn.close()
    return lead_id


def get_leads_by_status(status: str) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM leads WHERE status = ? ORDER BY created_at DESC", (status,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_lead_status(lead_id: int, status: str, **kwargs):
    conn = get_db()
    fields = {"status": status, **kwargs}
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    conn.execute(
        f"UPDATE leads SET {set_clause} WHERE id = ?",
        list(fields.values()) + [lead_id],
    )
    conn.commit()
    conn.close()


def log_email(lead_id: int, gmail_message_id: str, subject: str, body: str, template_type: str):
    conn = get_db()
    conn.execute(
        """INSERT INTO emails (lead_id, gmail_message_id, subject, body, template_type)
           VALUES (?, ?, ?, ?, ?)""",
        (lead_id, gmail_message_id, subject, body, template_type),
    )
    conn.commit()
    conn.close()


def get_leads_awaiting_followup(days_since_email: int = 3) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        """SELECT * FROM leads
           WHERE status = 'emailed'
           AND follow_up_count < 2
           AND email_sent_at < datetime('now', ?)
           ORDER BY email_sent_at ASC""",
        (f"-{days_since_email} days",),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
