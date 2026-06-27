"""
Lead enrichment — extracts email addresses from business websites.
No paid API needed: fetches the website and scrapes for mailto/email patterns.
"""

import re
import logging
import requests
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
_SKIP_DOMAINS = {"example.com", "sentry.io", "wix.com", "wordpress.com", "shopify.com"}
_CONTACT_PATHS = ["/contact", "/contact-us", "/about", "/about-us", "/reach-us", "/connect"]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36"
}


def _fetch(url: str, timeout: int = 8) -> str:
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        return r.text if r.status_code == 200 else ""
    except Exception:
        return ""


def _extract_emails(html: str, company_domain: str = "") -> list[str]:
    found = _EMAIL_RE.findall(html)
    clean = []
    seen = set()
    for e in found:
        e = e.lower().strip(".,;\"'")
        domain = e.split("@")[-1]
        if domain in _SKIP_DOMAINS:
            continue
        # Prefer emails on the same domain as the website
        if e not in seen:
            seen.add(e)
            clean.append(e)
    # Prioritize emails that share the company domain
    if company_domain:
        primary = [e for e in clean if company_domain in e]
        others  = [e for e in clean if company_domain not in e]
        clean = primary + others
    return clean


def find_email_from_website(website: str) -> str:
    """
    Try to find a contact email from a business website.
    Checks homepage + common contact page paths.
    Returns the best email found, or empty string.
    """
    if not website or "facebook.com" in website or "instagram.com" in website:
        return ""

    try:
        parsed = urlparse(website)
        domain = parsed.netloc.replace("www.", "")
    except Exception:
        return ""

    # 1. Try homepage
    html = _fetch(website)
    emails = _extract_emails(html, domain)
    if emails:
        logger.debug(f"  Found email on homepage: {emails[0]}")
        return emails[0]

    # 2. Try common contact pages
    base = f"{parsed.scheme}://{parsed.netloc}"
    for path in _CONTACT_PATHS:
        html = _fetch(urljoin(base, path))
        emails = _extract_emails(html, domain)
        if emails:
            logger.debug(f"  Found email on {path}: {emails[0]}")
            return emails[0]

    return ""


def enrich_leads_with_emails(conn) -> int:
    """
    For all leads with a website but no email, try to scrape the email.
    Returns count of leads enriched.
    """
    rows = conn.execute("""
        SELECT id, company, website FROM leads
        WHERE (email IS NULL OR email = '')
        AND website IS NOT NULL AND website != ''
    """).fetchall()

    enriched = 0
    for row in rows:
        lead_id, company, website = row["id"], row["company"], row["website"]
        logger.info(f"  Enriching {company} ({website})")
        email = find_email_from_website(website)
        if email:
            conn.execute("UPDATE leads SET email = ? WHERE id = ?", (email, lead_id))
            conn.commit()
            logger.info(f"    → {email}")
            enriched += 1
        else:
            logger.info(f"    → no email found")

    return enriched
