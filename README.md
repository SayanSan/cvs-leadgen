# CVS Lead Gen Machine 🤖

An autonomous multi-agent lead generation pipeline built for CVS. It finds B2B SaaS and CRM prospects, sends personalized cold emails, and books meetings — all on autopilot.

---

## How It Works

Three AI agents run in sequence, each handling one stage of the sales funnel:

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Scout Agent   │────▶│  Outreach Agent  │────▶│   Sales Agent   │
│                 │     │                  │     │                 │
│ LinkedIn scrape │     │ Claude generates │     │ Reads replies   │
│ Google Maps     │     │ personalized     │     │ Classifies intent│
│ Stores leads    │     │ cold emails      │     │ Books meetings  │
│ in SQLite CRM   │     │ Sends via Gmail  │     │ Syncs Calendly  │
└─────────────────┘     └──────────────────┘     └─────────────────┘
         │                       │                        │
         ▼                       ▼                        ▼
    new leads              status: emailed          status: replied
                                                  meeting_booked
```

### Agent 1 — Scout Agent
- Searches LinkedIn for decision-makers (CTOs, VPs, Founders) at SaaS and CRM companies
- Scrapes Google Maps for tech businesses in target Indian cities
- Deduplicates and stores all leads in a local SQLite database
- Powered by **Apify MCP** — no browser automation needed

### Agent 2 — Outreach Agent
- Picks up all `new` leads with email addresses
- Uses **Claude AI (Haiku)** to generate a hyper-personalized opening line and pain point for each lead
- Sends branded HTML emails via **Gmail API** with your portfolio and Calendly link
- Sends follow-up emails after 3 days of no reply (max 2 follow-ups per lead)

### Agent 3 — Sales Agent
- Polls Gmail inbox for replies from leads
- Uses **Claude AI** to classify each reply: `interested` / `not_interested` / `question` / `unsubscribe` / `auto_reply`
- Responds automatically:
  - **Interested** → sends Calendly booking link
  - **Question** → drafts a smart answer and includes Calendly link
  - **Unsubscribe** → marks lead as unsubscribed, never contacts again
- Syncs **Calendly** to detect bookings and marks leads as `meeting_booked`

---

## Lead Pipeline

Every lead moves through these statuses in the SQLite CRM:

```
new → emailed → replied → meeting_booked → closed
                        ↘ unsubscribed
                        ↘ not_interested
```

---

## Tech Stack

| Component | Tool |
|---|---|
| Lead Scraping | [Apify MCP](https://apify.com) — LinkedIn + Google Maps actors |
| Email Sending | Gmail API (OAuth 2.0) |
| AI Personalization | Anthropic Claude (claude-haiku-4-5) |
| Meeting Booking | Calendly API |
| Database | SQLite (local, zero-config) |
| Language | Python 3.11+ |

---

## Project Structure

```
cvs-leadgen/
├── agents/
│   ├── scout_agent.py        # Lead scraping from LinkedIn & Google Maps
│   ├── outreach_agent.py     # Email personalization & sending
│   └── sales_agent.py        # Reply handling & meeting booking
├── tools/
│   ├── apify_tools.py        # Apify actor wrappers
│   ├── gmail_tools.py        # Gmail send/read/reply
│   ├── calendly_tools.py     # Calendly events & invitees
│   └── db_tools.py           # SQLite CRM operations
├── templates/
│   └── emails.py             # HTML email templates (outreach, follow-up, meeting)
├── config.py                 # Centralized config from env vars
├── main.py                   # Pipeline orchestrator + dashboard
├── scheduler.py              # Cron-style scheduler for automated runs
├── .env.example              # Environment variable template
└── requirements.txt
```

---

## Setup

### 1. Clone & Install

```bash
git clone https://github.com/SayanSan/cvs-leadgen.git
cd cvs-leadgen
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
# Apify — lead scraping
APIFY_API_TOKEN=your_apify_token

# Gmail — sender identity
SENDER_EMAIL=you@yourcompany.com
SENDER_NAME=Your Name

# Anthropic — AI personalization
ANTHROPIC_API_KEY=sk-ant-...

# Calendly
CALENDLY_API_KEY=your_calendly_key
CALENDLY_MEETING_LINK=https://calendly.com/yourlink

# CVS company info (injected into emails)
COMPANY_NAME=CVS
COMPANY_PORTFOLIO_URL=https://yoursite.com/portfolio
COMPANY_DEMO_URL=https://yoursite.com/demo
COMPANY_WEBSITE=https://yoursite.com
```

### 3. Gmail OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a project → Enable **Gmail API**
3. Create OAuth 2.0 credentials → Download as `gmail_credentials.json`
4. Place `gmail_credentials.json` in the project root
5. Run once to authenticate:

```bash
python tools/gmail_tools.py --auth
```

A browser window will open for Google sign-in. Token is saved to `gmail_token.json` for future runs.

### 4. Apify Actors

The scout agent uses these Apify actors (all have a free tier):

| Actor | Purpose |
|---|---|
| `harvestapi/linkedin-profile-scraper` | LinkedIn people + email extraction |
| `harvestapi/linkedin-profile-search-scraper` | LinkedIn keyword search |
| `compass/crawler-google-places` | Google Maps business scraper |

---

## Usage

```bash
# Run the full pipeline (scout → outreach → sales)
python main.py

# Run individual agents
python main.py scout        # Only scrape new leads
python main.py outreach     # Only send emails
python main.py sales        # Only check replies + Calendly

# Dry run — simulate everything without sending emails
python main.py --dry-run

# View pipeline stats
python main.py dashboard
```

### Dashboard output

```
==================================================
   CVS Lead Gen Dashboard
==================================================
  Total Leads:       247
  With Email:        189
  Emails Sent:        93
--------------------------------------------------
  new                 58  ██████████████████████████████
  emailed             81  ██████████████████████████████
  replied             24  ████████████
  meeting_booked      12  ██████
  not_interested      18  █████████
  unsubscribed         9  ████
==================================================
```

### Automated Scheduling

Run the pipeline automatically every day:

```bash
python scheduler.py
```

Default schedule:
- **9:00 AM** — Scout Agent (find new leads)
- **10:00 AM** — Outreach Agent (send emails)
- **Every 2 hours** — Sales Agent (check replies)

---

## Email Templates

All three email types are in [`templates/emails.py`](templates/emails.py):

| Template | When sent |
|---|---|
| **Initial Outreach** | First contact — AI-personalized opener + portfolio |
| **Follow-up** | 3 days after no reply — different value angle + demo link |
| **Meeting Confirmation** | When lead replies interested — Calendly booking link |

---

## Target Leads

By default the scout searches for:

**LinkedIn:** CTOs, VPs of Engineering, Founders, Heads of Product at SaaS/CRM companies

**Google Maps:** SaaS companies, software development firms, CRM vendors across Bangalore, Mumbai, Delhi, Hyderabad, Pune

Customize search queries in [`agents/scout_agent.py`](agents/scout_agent.py) — `LINKEDIN_SEARCH_QUERIES` and `GOOGLE_MAPS_QUERIES`.

---

## Important Notes

- **Rate limits:** The pipeline sends max 20 emails per run by default. Increase `batch_size` in `main.py` carefully to avoid Gmail spam flags.
- **Unsubscribes:** Every email includes an unsubscribe instruction. The Sales Agent honors these automatically.
- **Email warmup:** If using a new Gmail account, warm it up gradually (5 → 10 → 20 emails/day) before running at full volume.
- **LinkedIn ToS:** Apify scrapers are compliant with LinkedIn's public data policy. Do not scrape private/gated profile data.

---

## License

MIT
