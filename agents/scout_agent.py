"""
Scout Agent — finds businesses that need websites, apps, and digital marketing.

Targets:
  - Local businesses with no/weak web presence (restaurants, clinics, salons, etc.)
  - Small businesses actively looking for digital services
  - Startups and SMEs needing mobile apps or web platforms
  - Businesses running offline with no digital marketing
"""

import json
import logging
import os
from tools.apify_tools import scrape_linkedin_people, scrape_google_maps, scrape_linkedin_companies
from tools.db_tools import upsert_lead, init_db, get_db
from tools.enrich_tools import enrich_leads_with_emails

logger = logging.getLogger(__name__)

_QUERIES_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "scout_queries.json")

def _load_custom_queries():
    """Load queries saved from the dashboard Settings page, if any."""
    if os.path.exists(_QUERIES_FILE):
        with open(_QUERIES_FILE) as f:
            data = json.load(f)
        google = [(row["query"], row["location"]) for row in data.get("google_maps", [])]
        linkedin = data.get("linkedin", [])
        return google or None, linkedin or None
    return None, None


# ---------------------------------------------------------------------------
# Google Maps — local businesses by category & city
# These are businesses likely to need a website, app, or digital marketing.
# ---------------------------------------------------------------------------
GOOGLE_MAPS_QUERIES = [
    # Businesses that rarely have good websites
    ("restaurant",              "Kolkata"),
    ("cafe",                    "Kolkata"),
    ("clothing store",          "Kolkata"),
    ("jewellery shop",          "Kolkata"),
    ("hardware store",          "Kolkata"),
    ("furniture store",         "Kolkata"),
    ("pharmacy",                "Kolkata"),
    ("gym fitness center",      "Kolkata"),
    ("beauty salon",            "Kolkata"),
    ("interior designer",       "Kolkata"),

    # Service businesses that need lead-gen websites
    ("CA chartered accountant", "Kolkata"),
    ("lawyer law firm",         "Kolkata"),
    ("real estate agent",       "Kolkata"),
    ("travel agency",           "Kolkata"),
    ("event management company","Kolkata"),
    ("wedding planner",         "Kolkata"),
    ("driving school",          "Kolkata"),
    ("coaching institute",      "Kolkata"),
    ("diagnostic centre",       "Kolkata"),
    ("dentist clinic",          "Kolkata"),

    # Small/mid businesses in other cities
    ("restaurant",              "Mumbai"),
    ("retail shop",             "Delhi"),
    ("clothing boutique",       "Bangalore"),
    ("beauty salon",            "Hyderabad"),
    ("coaching institute",      "Pune"),
    ("real estate agent",       "Chennai"),
    ("event management company","Ahmedabad"),
    ("restaurant",              "Jaipur"),
    ("hotel",                   "Goa"),
    ("travel agency",           "Kochi"),
]

# ---------------------------------------------------------------------------
# LinkedIn — decision-makers at small businesses and agencies
# ---------------------------------------------------------------------------
LINKEDIN_SEARCH_QUERIES = [
    "founder small business India website",
    "owner restaurant India digital marketing",
    "proprietor retail shop India",
    "managing director SME India no website",
    "founder startup India mobile app",
    "owner clinic hospital India website",
    "director school coaching India",
    "founder ecommerce India",
    "owner hotel hospitality India",
    "managing director manufacturing India website",
]


def run_scout(
    linkedin_queries: list[str] = None,
    google_queries: list[tuple] = None,
    max_per_query: int = 20,
    skip_linkedin: bool = False,
) -> dict:
    init_db()

    custom_google, custom_linkedin = _load_custom_queries()
    linkedin_queries = linkedin_queries or custom_linkedin or LINKEDIN_SEARCH_QUERIES
    google_queries   = google_queries   or custom_google   or GOOGLE_MAPS_QUERIES

    total_found = total_saved = total_with_email = 0

    # --- Google Maps (primary source — highest signal for local biz) ---
    logger.info(f"Starting Google Maps scrape with {len(google_queries)} queries")
    for query, location in google_queries:
        try:
            leads = scrape_google_maps(query, location, max_results=max_per_query)
            logger.info(f"  [{query}, {location}] found {len(leads)} businesses")
            for lead in leads:
                total_found += 1
                # Tag the service need based on query keyword
                lead["service_needed"] = _infer_service(query, lead)
                if lead.get("email"):
                    total_with_email += 1
                upsert_lead(lead)
                total_saved += 1
        except Exception as e:
            logger.error(f"Google Maps scrape failed for '{query} {location}': {e}")

    # --- LinkedIn (secondary — decision-maker contacts) ---
    if not skip_linkedin:
        logger.info(f"Starting LinkedIn scrape with {len(linkedin_queries)} queries")
        for query in linkedin_queries:
            try:
                leads = scrape_linkedin_people(query, max_results=max_per_query)
                logger.info(f"  [{query}] found {len(leads)} profiles")
                for lead in leads:
                    total_found += 1
                    lead["service_needed"] = _infer_service(query, lead)
                    if lead.get("email"):
                        total_with_email += 1
                    upsert_lead(lead)
                    total_saved += 1
            except Exception as e:
                logger.error(f"LinkedIn scrape failed for '{query}': {e}")

    # Enrich leads that have a website but no email
    logger.info("Enriching leads — scraping websites for contact emails...")
    conn = get_db()
    enriched = enrich_leads_with_emails(conn)
    conn.close()
    logger.info(f"  Enriched {enriched} leads with emails from their websites")

    # Recount emails after enrichment
    conn = get_db()
    total_with_email = conn.execute(
        "SELECT COUNT(*) FROM leads WHERE email != '' AND email IS NOT NULL"
    ).fetchone()[0]
    conn.close()

    summary = {
        "total_found": total_found,
        "total_with_email": total_with_email,
        "total_saved": total_saved,
        "enriched": enriched,
    }
    logger.info(f"Scout Agent complete: {summary}")
    return summary


# ---------------------------------------------------------------------------
# Infer what service the lead likely needs
# ---------------------------------------------------------------------------
_SERVICE_MAP = {
    # Needs a website
    "restaurant": "website",
    "cafe": "website",
    "pharmacy": "website",
    "clinic": "website",
    "dentist": "website",
    "diagnostic": "website",
    "jewellery": "website",
    "hardware": "website",
    "furniture": "website",
    "clothing": "website",
    "boutique": "website",
    "hotel": "website",
    "driving school": "website",
    "coaching": "website",

    # Needs digital marketing
    "retail": "digital_marketing",
    "salon": "digital_marketing",
    "beauty": "digital_marketing",
    "gym": "digital_marketing",
    "fitness": "digital_marketing",
    "travel agency": "digital_marketing",
    "wedding": "digital_marketing",
    "event": "digital_marketing",

    # Needs a web/mobile app
    "real estate": "web_app",
    "interior": "web_app",
    "ca ": "web_app",
    "chartered": "web_app",
    "lawyer": "web_app",
    "law firm": "web_app",
    "ecommerce": "web_app",
    "startup": "web_app",
    "mobile app": "web_app",
    "manufacturing": "web_app",
}

def _infer_service(query: str, lead: dict) -> str:
    text = (query + " " + (lead.get("industry") or "") + " " + (lead.get("title") or "")).lower()
    for keyword, service in _SERVICE_MAP.items():
        if keyword in text:
            return service
    return "website"  # default — most businesses need a website first


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s — %(message)s")
    result = run_scout(max_per_query=15, skip_linkedin=True)
    print(f"\nScout done: {result}")
