"""
Apify-based scrapers for LinkedIn and Google Maps.

Actors used:
  - Google Maps Scraper:      AmqbKSb0W0EqqVBj6  (compass/google-maps-scraper)
  - LinkedIn Profile Scraper: harvestapi/linkedin-profile-scraper
  - LinkedIn Company Search:  curious_coder/linkedin-company-search-scraper
"""

from apify_client import ApifyClient
from config import config

client = ApifyClient(config.APIFY_API_TOKEN)


def _run_actor(actor_id: str, run_input: dict) -> list[dict]:
    """Run an Apify actor and return all result items."""
    run = client.actor(actor_id).call(run_input=run_input)
    if not run or not run.get("defaultDatasetId"):
        return []
    return list(client.dataset(run["defaultDatasetId"]).iterate_items())


def scrape_google_maps(
    query: str,
    location: str = "",
    max_results: int = 20,
) -> list[dict]:
    """
    Scrape Google Maps businesses using actor AmqbKSb0W0EqqVBj6.
    Returns normalized lead dicts.
    """
    search_term = f"{query} {location}".strip()
    raw = _run_actor(
        "AmqbKSb0W0EqqVBj6",
        {
            "searchQueries": [search_term],
            "maxResults": max_results,
            "proxyConfig": {"useApifyProxy": True},
        },
    )
    leads = []
    for item in raw:
        leads.append({
            "name": item.get("name", ""),
            "company": item.get("name", ""),
            "title": "Business Owner",
            "email": item.get("email", ""),
            "phone": item.get("phone", ""),
            "website": item.get("website", ""),
            "location": item.get("address", ""),
            "linkedin_url": "",
            "source": "google_maps",
            "industry": item.get("category", query),
            "company_size": "",
        })
    return leads


def scrape_linkedin_people(
    keywords: str,
    location: str = "",
    max_results: int = 20,
) -> list[dict]:
    """
    Search LinkedIn for people using actor M2FMdjRVeF1HPGFcc.
    Returns normalized lead dicts.
    """
    raw = _run_actor(
        "M2FMdjRVeF1HPGFcc",
        {
            "profileScraperMode": "Full",
            "searchQuery": keywords,
            "maxItems": max_results,
            "locations": [location] if location else None,
            "startPage": 1,
        },
    )
    leads = []
    for item in raw:
        # Actor returns nested experience/position data
        positions = item.get("positions") or item.get("experience") or []
        current = positions[0] if positions else {}
        leads.append({
            "name": item.get("fullName") or item.get("name", ""),
            "title": item.get("headline") or current.get("title", ""),
            "company": current.get("companyName") or item.get("companyName", ""),
            "location": item.get("location") or item.get("geoLocation", ""),
            "linkedin_url": item.get("profileUrl") or item.get("linkedInUrl", ""),
            "email": item.get("email", ""),
            "source": "linkedin",
            "industry": item.get("industry", ""),
            "company_size": item.get("companyHeadcount", ""),
        })
    return leads


def scrape_linkedin_companies(
    keywords: str,
    max_results: int = 30,
) -> list[dict]:
    """
    Search LinkedIn for companies matching keywords.
    """
    raw = _run_actor(
        "curious_coder/linkedin-company-search-scraper",
        {
            "searchTerms": [keywords],
            "maxResults": max_results,
        },
    )
    leads = []
    for item in raw:
        leads.append({
            "name": "",
            "company": item.get("name", ""),
            "title": "Decision Maker",
            "email": item.get("email", ""),
            "linkedin_url": item.get("linkedinUrl", ""),
            "website": item.get("website", ""),
            "source": "linkedin_company",
            "industry": item.get("industry", ""),
            "company_size": item.get("staffCount", ""),
            "location": item.get("headquarters", ""),
        })
    return leads
