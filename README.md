# CVS LeadGen — Automated Lead Generation Machine

An end-to-end automated lead generation system built for **Code Visionary Services** — finds businesses that need websites, mobile apps, and digital marketing, then reaches out with personalized emails and auto-generated demo pages.

---

## What It Does

```
Scout Agent → Outreach Agent → Sales Agent
     ↓               ↓               ↓
Find leads     Send emails      Monitor replies
(Google Maps   with custom      & book meetings
 + LinkedIn)   demo pages       via Calendly
```

1. **Scout Agent** — scrapes Google Maps and LinkedIn for local businesses across Indian cities that need digital services (restaurants, salons, clinics, retail shops, real estate agents, coaching institutes, etc.)
2. **Outreach Agent** — generates a personalized demo page per lead and sends a tailored email with the demo link
3. **Sales Agent** — monitors inbox for replies, classifies intent (interested / question / unsubscribe), responds automatically, and syncs meeting bookings from Calendly
4. **Web Dashboard** — full management UI to view leads, run agents, and watch live logs

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Lead Scraping | [Apify](https://apify.com) — Google Maps Scraper + LinkedIn Profile Scraper |
| Email | Gmail API (OAuth 2.0) |
| Meetings | Calendly REST API |
| Database | SQLite (local CRM) |
| Web Server | FastAPI + Uvicorn |
| Demo Pages | Static HTML hosted on GitHub Pages |
| Hosting | Railway |
| Language | Python 3.9+ |

---

## Lead Pipeline

```
new → emailed → replied → meeting_booked → closed
```

Each lead also gets a `service_needed` tag: `website` / `web_app` / `digital_marketing`

---

## Target Industries & Cities

**Industries (Google Maps):**
- Restaurants, Cafes, Hotels
- Beauty Salons, Gyms, Fitness Centers
- Clinics, Dentists, Diagnostic Centres
- Clothing, Jewellery, Furniture Stores
- Real Estate Agents, Interior Designers
- CA / Chartered Accountants, Lawyers
- Travel Agencies, Event & Wedding Planners
- Coaching Institutes, Driving Schools
- Retail Shops, Hardware Stores, Pharmacies
- Manufacturing Companies

**Cities:** Kolkata, Mumbai, Delhi, Bangalore, Hyderabad, Pune, Chennai, Ahmedabad, Jaipur, Goa, Kochi

---

## Project Structure

```
cvs-leadgen/
├── agents/
│   ├── scout_agent.py       # Finds leads via Apify
│   ├── outreach_agent.py    # Personalizes & sends emails
│   └── sales_agent.py       # Monitors replies & books meetings
├── tools/
│   ├── apify_tools.py       # Google Maps + LinkedIn scrapers
│   ├── db_tools.py          # SQLite CRM (upsert, status updates)
│   ├── gmail_tools.py       # Gmail API (send, read, OAuth)
│   └── calendly_tools.py    # Calendly event sync
├── templates/
│   ├── emails.py            # Email templates (outreach, follow-up, meeting)
│   └── demo_pages.py        # Personalized HTML demo page generator
├── docs/
│   └── demos/               # Auto-generated demo pages (served via GitHub Pages)
├── data/
│   └── leads.db             # SQLite database (gitignored)
├── server.py                # FastAPI web dashboard
├── main.py                  # CLI runner
├── scheduler.py             # Automated daily schedule
├── config.py                # Env-based config
├── requirements.txt
├── railway.toml             # Railway deployment config
└── Procfile
```

---

## Setup

### 1. Clone & install

```bash
git clone https://github.com/SayanSan/cvs-leadgen.git
cd cvs-leadgen
pip3 install -r requirements.txt
```

### 2. Configure `.env`

```env
# Apify (get free token at apify.com)
APIFY_API_TOKEN=your_apify_token

# Gmail
SENDER_EMAIL=you@yourdomain.com
SENDER_NAME=Your Name | Company Name

# Calendly
CALENDLY_API_KEY=your_calendly_token
CALENDLY_MEETING_LINK=https://calendly.com/your-link/30min

# Company info
COMPANY_NAME=Your Company Name
COMPANY_WEBSITE=https://yourwebsite.com
COMPANY_PORTFOLIO_URL=https://yourwebsite.com/portfolio
```

### 3. Gmail OAuth (one-time)

```bash
PYTHONPATH=. python3 tools/gmail_tools.py --auth
```
A browser opens → log in → approve → `gmail_token.json` is saved.

### 4. Enable GitHub Pages

Go to your repo → **Settings → Pages → Source: main branch, /docs folder** → Save.

Demo pages will be live at `https://yourusername.github.io/cvs-leadgen/demos/company-name.html`

---

## Usage

### Run manually

```bash
# Find leads
PYTHONPATH=. python3 main.py scout

# Send outreach emails (generates & publishes demos automatically)
PYTHONPATH=. python3 main.py outreach

# Monitor replies and book meetings
PYTHONPATH=. python3 main.py sales

# Send follow-ups to leads with no reply after 3 days
PYTHONPATH=. python3 main.py followups

# See dashboard stats in terminal
PYTHONPATH=. python3 main.py dashboard
```

### Dry run (no emails sent)

```bash
PYTHONPATH=. python3 main.py outreach --dry-run
```

### Start the web dashboard

```bash
PYTHONPATH=. python3 -m uvicorn server:app --host 0.0.0.0 --port 8000
```
Open [http://localhost:8000](http://localhost:8000)

### Run on a schedule (daily automation)

```bash
PYTHONPATH=. python3 scheduler.py
```

Schedule:
- **8:00 AM** — Scout Agent (find new leads)
- **9:00 AM** — Outreach Agent (send emails)
- **12:00 PM & 5:00 PM** — Sales Agent (check replies)
- **Every 3 days** — Follow-up Agent

---

## Deploy to Railway

1. Go to [railway.app](https://railway.app) → **New Project → Deploy from GitHub** → select this repo
2. Add environment variables in Railway's **Variables** tab (same as `.env`)
3. Railway auto-deploys on every `git push` — your dashboard is live at the Railway URL

---

## How Demo Pages Work

When Outreach Agent emails a lead, it:
1. Generates a personalized HTML dashboard for their business (industry-matched: retail, real estate, SaaS, or generic)
2. Saves it to `docs/demos/<company-slug>.html`
3. Commits and pushes to GitHub — GitHub Pages serves it instantly
4. Includes the link in the email with a "View Your Personalized Demo" button

When a lead replies with interest, Sales Agent regenerates a richer version and re-sends it.

---

## No AI API Required

All personalization is rule-based — no OpenAI or Anthropic API key needed:
- Email openers matched by job title keywords
- Pain points matched by industry keywords
- Reply intent classified by keyword matching (interested / unsubscribe / question / auto-reply)

---

## Security

- `.env` is gitignored — never committed
- `gmail_credentials.json` and `gmail_token.json` are gitignored
- Apify token stored in `.env` only

---

## Built by

**Sayan Choudhury** — [Code Visionary Services](https://codevisionaryservices.com)
`sayan@codevisionaryservices.com`
