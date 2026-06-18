import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    # Apify - for LinkedIn & Google Maps scraping
    # Get free API token at https://apify.com
    APIFY_API_TOKEN: str = os.getenv("APIFY_API_TOKEN", "")

    # Gmail OAuth credentials
    # Create at https://console.cloud.google.com → Gmail API → OAuth 2.0
    GMAIL_CREDENTIALS_FILE: str = os.getenv("GMAIL_CREDENTIALS_FILE", "gmail_credentials.json")
    GMAIL_TOKEN_FILE: str = os.getenv("GMAIL_TOKEN_FILE", "gmail_token.json")
    SENDER_EMAIL: str = os.getenv("SENDER_EMAIL", "")
    SENDER_NAME: str = os.getenv("SENDER_NAME", "CVS Team")

    # Calendly
    # Get at https://calendly.com/integrations/api_webhooks
    CALENDLY_API_KEY: str = os.getenv("CALENDLY_API_KEY", "")
    CALENDLY_MEETING_LINK: str = os.getenv("CALENDLY_MEETING_LINK", "")

    # SQLite DB path
    DB_PATH: str = os.getenv("DB_PATH", "data/leads.db")

    # Company info (injected into email templates)
    COMPANY_NAME: str = "CVS"
    COMPANY_PORTFOLIO_URL: str = os.getenv("COMPANY_PORTFOLIO_URL", "")
    COMPANY_DEMO_URL: str = os.getenv("COMPANY_DEMO_URL", "")
    COMPANY_WEBSITE: str = os.getenv("COMPANY_WEBSITE", "")

    # Lead gen targeting
    TARGET_INDUSTRIES: list = None
    TARGET_COMPANY_SIZES: list = None

    def __post_init__(self):
        if self.TARGET_INDUSTRIES is None:
            self.TARGET_INDUSTRIES = ["SaaS", "Software", "Technology", "CRM"]
        if self.TARGET_COMPANY_SIZES is None:
            self.TARGET_COMPANY_SIZES = ["1-10", "11-50", "51-200"]


config = Config()
