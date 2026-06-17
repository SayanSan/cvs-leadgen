"""
Apify-based scrapers for LinkedIn and Google Maps.

Actors used (all have free tier):
  - LinkedIn People Search: apify/linkedin-profile-scraper
  - LinkedIn Company Search: curious_coder/linkedin-company-search-scraper
  - Google Maps Scraper: apify/google-maps-scraper
"""

import time
import requests
from config import config


APIFY_BASE = "https://api.apify.com/v2"
HEADERS = {"Authorization": f"Bearer {config.APIFY_API_TOKEN}"}


def _run_actor(actor_id: str, run_input: dict, timeout_secs: int = 120) -> list[dict]:
    """Start an Apify actor run and wait for results."""
    r = requests.post(
        f"{APIFY_BASE}/acts/{actor_id}/runs",
        headers=HEADERS,
        json={"runInput": run_input, "timeout": timeout_secs},
        params={"token": config.APIFY_API_TOKEN},
    )
    r.raise_for_status()
    run_id = r.json()["data"]["id"]
    dataset_id = r.json()["data"]["defaultDatasetId"]

    # Poll until finished
    for _ in range(timeout_secs // 5):
        status_r = requests.get(
            f"{APIFY_BASE}/actor-runs/{run_id}",
            params={"token": config.APIFY_API_TOKEN},
        )
        status = status_r.json()["data"]["status"]
        if status == "SUCCEEDED":
            break
        if status in ("FAILED", "ABORTED", "TIMED-OUT"):
            raise RuntimeError(f"Apify actor {actor_id} failed with status: {status}")
        time.sleep(5)

    items_r = requests.get(
        f"{APIFY_BASE}/datasets/{dataset_id}/items",
        params={"token": config.APIFY_API_TOKEN, "format": "json"},
    )
    items_r.raise_for_status()
    return items_r.json()


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


def scrape_google_maps(
    query: str,
    location: str = "",
    max_results: int = 50,
) -> list[dict]:
    """
    Search Google Maps for businesses (e.g. 'SaaS company Mumbai').
    Returns normalized lead dicts.
    """
    search_term = f"{query} {location}".strip()
    raw = _run_actor(
        "compass/crawler-google-places",
        {
            "searchStringsArray": [search_term],
            "maxCrawledPlacesPerSearch": max_results,
            "language": "en",
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


def scrape_linkedin_companies(
    keywords: str,
    max_results: int = 30,
) -> list[dict]:
    """
    Search LinkedIn for companies matching keywords.
    Returns companies (use for Account-Based outreach).
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
