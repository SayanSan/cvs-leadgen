"""
Scout Agent — finds and stores leads from LinkedIn and Google Maps.

Responsibilities:
  1. Search LinkedIn for decision-makers at B2B SaaS & CRM companies
  2. Search Google Maps for tech companies in target locations
  3. Deduplicate and store all leads in SQLite
  4. Skip leads without email (they need manual enrichment or Hunter.io)
"""

import logging
from tools.apify_tools import scrape_linkedin_people, scrape_google_maps, scrape_linkedin_companies
from tools.db_tools import upsert_lead, init_db

logger = logging.getLogger(__name__)


LINKEDIN_SEARCH_QUERIES = [
    "CTO SaaS startup",
    "VP Engineering custom CRM",
    "Head of Product B2B software",
    "Founder SaaS company",
    "CTO software development company",
    "Head of Sales Operations CRM",
    "Director of Engineering startup",
]

GOOGLE_MAPS_QUERIES = [
    ("SaaS company", "Bangalore"),
    ("software development company", "Mumbai"),
    ("CRM software company", "Delhi"),
    ("tech startup", "Hyderabad"),
    ("software company", "Pune"),
]


def run_scout(
    linkedin_queries: list[str] = None,
    google_queries: list[tuple] = None,
    max_per_query: int = 30,
) -> dict:
    """
    Main entry point for the Scout Agent.
    Returns summary of leads found.
    """
    init_db()

    linkedin_queries = linkedin_queries or LINKEDIN_SEARCH_QUERIES
    google_queries = google_queries or GOOGLE_MAPS_QUERIES

    total_found = 0
    total_with_email = 0
    total_saved = 0

    # --- LinkedIn People ---
    logger.info(f"Starting LinkedIn scrape with {len(linkedin_queries)} queries")
    for query in linkedin_queries:
        try:
            leads = scrape_linkedin_people(query, max_results=max_per_query)
            logger.info(f"  [{query}] found {len(leads)} profiles")
            for lead in leads:
                total_found += 1
                if lead.get("email"):
                    total_with_email += 1
                    upsert_lead(lead)
                    total_saved += 1
                else:
                    # Store without email for later enrichment
                    upsert_lead(lead)
                    total_saved += 1
        except Exception as e:
            logger.error(f"LinkedIn scrape failed for '{query}': {e}")

    # --- Google Maps ---
    logger.info(f"Starting Google Maps scrape with {len(google_queries)} queries")
    for query, location in google_queries:
        try:
            leads = scrape_google_maps(query, location, max_results=max_per_query)
            logger.info(f"  [{query}, {location}] found {len(leads)} businesses")
            for lead in leads:
                total_found += 1
                if lead.get("email"):
                    total_with_email += 1
                upsert_lead(lead)
                total_saved += 1
        except Exception as e:
            logger.error(f"Google Maps scrape failed for '{query} {location}': {e}")

    summary = {
        "total_found": total_found,
        "total_with_email": total_with_email,
        "total_saved": total_saved,
    }
    logger.info(f"Scout Agent complete: {summary}")
    return summary


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    result = run_scout(max_per_query=20)
    print(f"\nScout done: {result}")
