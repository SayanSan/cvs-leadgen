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
    return list(client.dataset(run["defaultDatasetId"]).iterate_items())


def scrape_google_maps(
    query: str,
    location: str = "",
    max_results: int = 50,
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
            "proxyConfig": {
                "useApifyProxy": True,
                "apifyProxyGroups": ["RESIDENTIAL"],
            },
        },
    )
    leads = []
    for item in raw:
        leads.append({
            "name": item.get("title", ""),
            "company": item.get("title", ""),
            "title": "Business Owner",
            "email": item.get("email", ""),
            "phone": item.get("phone", ""),
            "website": item.get("website", ""),
            "location": item.get("address", ""),
            "linkedin_url": "",
            "source": "google_maps",
            "industry": query,
            "company_size": "",
        })
    return leads


def scrape_linkedin_people(
    keywords: str,
    location: str = "",
    max_results: int = 50,
) -> list[dict]:
    """
    Search LinkedIn for people matching keywords (e.g. 'CTO SaaS startup').
    Returns normalized lead dicts.
    """
    raw = _run_actor(
        "harvestapi/linkedin-profile-scraper",
        {
            "searchTerms": [keywords],
            "location": location,
            "maxResults": max_results,
        },
    )
    leads = []
    for item in raw:
        leads.append({
            "name": item.get("fullName") or item.get("name", ""),
            "title": item.get("headline") or item.get("title", ""),
            "company": item.get("companyName") or item.get("company", ""),
            "location": item.get("location", ""),
            "linkedin_url": item.get("profileUrl") or item.get("linkedinUrl", ""),
            "email": item.get("email", ""),
            "source": "linkedin",
            "industry": item.get("industry", ""),
            "company_size": item.get("companySize", ""),
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
