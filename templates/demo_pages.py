"""
Generates personalized HTML demo pages per lead, hosted via GitHub Pages.
Industry-specific templates show a mock CRM/dashboard tailored to the lead's business.
"""

import os
import re
import subprocess
import logging
from config import config

logger = logging.getLogger(__name__)

GITHUB_PAGES_BASE = "https://sayansan.github.io/cvs-leadgen/demos"
DEMOS_DIR = os.path.join(os.path.dirname(__file__), "..", "docs", "demos")

# ---------------------------------------------------------------------------
# Shared CSS / layout
# ---------------------------------------------------------------------------
_BASE_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Segoe UI', Arial, sans-serif; background: #f0f2f5; color: #1a1a2e; }
.topbar { background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); color: #fff; padding: 16px 32px; display: flex; align-items: center; justify-content: space-between; }
.topbar .logo { font-size: 20px; font-weight: 700; letter-spacing: 0.5px; }
.topbar .logo span { color: #00d4ff; }
.topbar .badge { background: #00d4ff; color: #000; font-size: 11px; font-weight: 700; padding: 3px 10px; border-radius: 20px; }
.hero { background: #fff; padding: 40px 32px 32px; border-bottom: 1px solid #e8eaf0; }
.hero h1 { font-size: 26px; font-weight: 700; margin-bottom: 8px; }
.hero h1 span { color: #0066ff; }
.hero p { color: #666; font-size: 15px; max-width: 600px; }
.hero .cta { margin-top: 20px; display: flex; gap: 12px; flex-wrap: wrap; }
.btn { padding: 11px 24px; border-radius: 8px; font-size: 14px; font-weight: 600; cursor: pointer; border: none; text-decoration: none; display: inline-block; }
.btn-primary { background: #0066ff; color: #fff; }
.btn-secondary { background: #f0f2f5; color: #1a1a2e; border: 1px solid #dde1ea; }
.dashboard { display: grid; grid-template-columns: 240px 1fr; min-height: calc(100vh - 130px); }
.sidebar { background: #fff; border-right: 1px solid #e8eaf0; padding: 24px 0; }
.sidebar-section { padding: 8px 16px; font-size: 11px; font-weight: 700; color: #999; text-transform: uppercase; letter-spacing: 1px; margin: 16px 0 4px; }
.sidebar-item { padding: 10px 20px; font-size: 14px; color: #555; cursor: pointer; display: flex; align-items: center; gap: 10px; border-radius: 0 8px 8px 0; margin-right: 12px; }
.sidebar-item.active { background: #eff4ff; color: #0066ff; font-weight: 600; }
.sidebar-item .icon { font-size: 16px; }
.content { padding: 28px; }
.stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px; }
.stat-card { background: #fff; padding: 20px; border-radius: 12px; border: 1px solid #e8eaf0; }
.stat-label { font-size: 12px; color: #999; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; }
.stat-value { font-size: 28px; font-weight: 700; color: #1a1a2e; }
.stat-delta { font-size: 12px; color: #00b359; margin-top: 4px; }
.panel { background: #fff; border-radius: 12px; border: 1px solid #e8eaf0; margin-bottom: 20px; }
.panel-header { padding: 16px 20px; border-bottom: 1px solid #e8eaf0; display: flex; align-items: center; justify-content: space-between; }
.panel-title { font-size: 15px; font-weight: 600; }
.panel-body { padding: 0; }
table { width: 100%; border-collapse: collapse; }
th { padding: 10px 16px; text-align: left; font-size: 11px; font-weight: 700; color: #999; text-transform: uppercase; letter-spacing: 0.5px; background: #f8f9fc; }
td { padding: 13px 16px; font-size: 14px; border-top: 1px solid #f0f2f5; color: #333; }
tr:hover td { background: #f8f9fc; }
.badge-pill { padding: 3px 10px; border-radius: 20px; font-size: 12px; font-weight: 600; }
.badge-green { background: #d4f5e2; color: #007a38; }
.badge-blue { background: #ddeeff; color: #004ecc; }
.badge-orange { background: #fff0db; color: #c45c00; }
.badge-grey { background: #f0f2f5; color: #666; }
.cta-footer { background: linear-gradient(135deg, #0066ff 0%, #0044cc 100%); color: #fff; padding: 36px 32px; text-align: center; }
.cta-footer h2 { font-size: 22px; font-weight: 700; margin-bottom: 10px; }
.cta-footer p { opacity: 0.85; margin-bottom: 20px; font-size: 15px; }
.cta-footer .btn { background: #fff; color: #0066ff; font-size: 15px; }
.watermark { font-size: 12px; opacity: 0.6; margin-top: 12px; }
"""

_FOOTER_HTML = """
<div class="cta-footer">
  <h2>Ready to build this for {company}?</h2>
  <p>This is a preview of what a custom CRM built specifically for {company} could look like.<br>
     Sayan at Code Visionary Services can have a working version live in 4–6 weeks.</p>
  <a href="{calendly}" class="btn" target="_blank">Book a Free 20-Min Strategy Call</a>
  <div class="watermark">Built with ❤ by Code Visionary Services · codevisionaryservices.com</div>
</div>
"""

# ---------------------------------------------------------------------------
# Industry templates
# ---------------------------------------------------------------------------

def _saas_template(company: str) -> str:
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{company} — CRM Preview</title>
<style>{_BASE_CSS}</style></head><body>
<div class="topbar">
  <div class="logo">{company} <span>CRM</span></div>
  <div class="badge">PREVIEW BUILD</div>
</div>
<div class="hero">
  <h1>Welcome back, <span>{company}</span> Team 👋</h1>
  <p>Your unified SaaS customer lifecycle dashboard — trials, conversions, churn risk, and MRR all in one place.</p>
  <div class="cta">
    <a href="{config.CALENDLY_MEETING_LINK}" class="btn btn-primary" target="_blank">Book a Call to Build This</a>
    <a href="https://codevisionaryservices.com/portfolio" class="btn btn-secondary" target="_blank">See Our Work</a>
  </div>
</div>
<div class="dashboard">
  <div class="sidebar">
    <div class="sidebar-section">Overview</div>
    <div class="sidebar-item active"><span class="icon">📊</span> Dashboard</div>
    <div class="sidebar-item"><span class="icon">👥</span> Customers</div>
    <div class="sidebar-item"><span class="icon">🧪</span> Trials</div>
    <div class="sidebar-section">Revenue</div>
    <div class="sidebar-item"><span class="icon">💳</span> Subscriptions</div>
    <div class="sidebar-item"><span class="icon">📈</span> MRR / ARR</div>
    <div class="sidebar-item"><span class="icon">⚠️</span> Churn Risk</div>
    <div class="sidebar-section">Support</div>
    <div class="sidebar-item"><span class="icon">🎫</span> Tickets</div>
    <div class="sidebar-item"><span class="icon">🔔</span> Alerts</div>
  </div>
  <div class="content">
    <div class="stats">
      <div class="stat-card"><div class="stat-label">MRR</div><div class="stat-value">$42,800</div><div class="stat-delta">↑ 12% this month</div></div>
      <div class="stat-card"><div class="stat-label">Active Customers</div><div class="stat-value">318</div><div class="stat-delta">↑ 24 new this week</div></div>
      <div class="stat-card"><div class="stat-label">Trial → Paid</div><div class="stat-value">68%</div><div class="stat-delta">↑ 5pts vs last month</div></div>
      <div class="stat-card"><div class="stat-label">Churn Risk</div><div class="stat-value">9</div><div class="stat-delta" style="color:#e03">3 critical</div></div>
    </div>
    <div class="panel">
      <div class="panel-header"><span class="panel-title">Active Trials → Conversion Pipeline</span><span class="badge-pill badge-blue">Live</span></div>
      <div class="panel-body"><table>
        <tr><th>Company</th><th>Trial Day</th><th>Usage</th><th>Last Active</th><th>Status</th></tr>
        <tr><td>Acme Corp</td><td>Day 11</td><td>87%</td><td>Today</td><td><span class="badge-pill badge-green">Hot Lead</span></td></tr>
        <tr><td>ByteWorks</td><td>Day 7</td><td>52%</td><td>Yesterday</td><td><span class="badge-pill badge-blue">On Track</span></td></tr>
        <tr><td>NovaSoft</td><td>Day 13</td><td>21%</td><td>3 days ago</td><td><span class="badge-pill badge-orange">At Risk</span></td></tr>
        <tr><td>CloudPeak</td><td>Day 2</td><td>95%</td><td>Today</td><td><span class="badge-pill badge-green">Hot Lead</span></td></tr>
      </table></div>
    </div>
    <div class="panel">
      <div class="panel-header"><span class="panel-title">Churn Risk Alerts</span></div>
      <div class="panel-body"><table>
        <tr><th>Customer</th><th>MRR</th><th>Signal</th><th>Days Inactive</th><th>Action</th></tr>
        <tr><td>TechBase Inc</td><td>$1,200</td><td>Login drop</td><td>8</td><td><span class="badge-pill badge-orange">Email Sequence</span></td></tr>
        <tr><td>Loop Analytics</td><td>$840</td><td>No API calls</td><td>12</td><td><span class="badge-pill badge-orange">CS Call</span></td></tr>
      </table></div>
    </div>
  </div>
</div>
{_FOOTER_HTML.format(company=company, calendly=config.CALENDLY_MEETING_LINK)}
</body></html>"""


def _realestate_template(company: str) -> str:
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{company} — Pipeline CRM Preview</title>
<style>{_BASE_CSS}</style></head><body>
<div class="topbar">
  <div class="logo">{company} <span>Pipeline</span></div>
  <div class="badge">PREVIEW BUILD</div>
</div>
<div class="hero">
  <h1>Your <span>{company}</span> Deal Tracker</h1>
  <p>From first inquiry to close — every lead, showing, offer, and commission tracked in one place built for how you actually sell.</p>
  <div class="cta">
    <a href="{config.CALENDLY_MEETING_LINK}" class="btn btn-primary" target="_blank">Book a Call to Build This</a>
    <a href="https://codevisionaryservices.com/portfolio" class="btn btn-secondary" target="_blank">See Our Work</a>
  </div>
</div>
<div class="dashboard">
  <div class="sidebar">
    <div class="sidebar-section">Sales Pipeline</div>
    <div class="sidebar-item active"><span class="icon">🏠</span> Active Listings</div>
    <div class="sidebar-item"><span class="icon">👤</span> Buyer Leads</div>
    <div class="sidebar-item"><span class="icon">📅</span> Showings</div>
    <div class="sidebar-section">Transactions</div>
    <div class="sidebar-item"><span class="icon">📝</span> Under Contract</div>
    <div class="sidebar-item"><span class="icon">✅</span> Closed Deals</div>
    <div class="sidebar-item"><span class="icon">💰</span> Commission Tracker</div>
    <div class="sidebar-section">Marketing</div>
    <div class="sidebar-item"><span class="icon">📣</span> Campaigns</div>
  </div>
  <div class="content">
    <div class="stats">
      <div class="stat-card"><div class="stat-label">Active Listings</div><div class="stat-value">24</div><div class="stat-delta">↑ 3 new this week</div></div>
      <div class="stat-card"><div class="stat-label">Pipeline Value</div><div class="stat-value">$6.2M</div><div class="stat-delta">8 deals in progress</div></div>
      <div class="stat-card"><div class="stat-label">Showings This Month</div><div class="stat-value">47</div><div class="stat-delta">↑ 18% vs last month</div></div>
      <div class="stat-card"><div class="stat-label">Commissions YTD</div><div class="stat-value">$138K</div><div class="stat-delta">On track for $200K</div></div>
    </div>
    <div class="panel">
      <div class="panel-header"><span class="panel-title">Active Deal Pipeline</span><span class="badge-pill badge-blue">8 Deals</span></div>
      <div class="panel-body"><table>
        <tr><th>Property</th><th>Buyer</th><th>Value</th><th>Stage</th><th>Next Step</th></tr>
        <tr><td>42 Oak Street</td><td>Johnson Family</td><td>$485,000</td><td><span class="badge-pill badge-green">Under Contract</span></td><td>Inspection 12/22</td></tr>
        <tr><td>17 Maple Ave</td><td>Chen Wei</td><td>$720,000</td><td><span class="badge-pill badge-blue">Offer Made</span></td><td>Counter offer due</td></tr>
        <tr><td>8 Pine Ridge</td><td>Martinez, R.</td><td>$310,000</td><td><span class="badge-pill badge-orange">Showing Scheduled</span></td><td>Sat 2pm</td></tr>
        <tr><td>201 Elm Court</td><td>Singh Family</td><td>$550,000</td><td><span class="badge-pill badge-grey">New Lead</span></td><td>Call back today</td></tr>
      </table></div>
    </div>
    <div class="panel">
      <div class="panel-header"><span class="panel-title">Upcoming Showings</span></div>
      <div class="panel-body"><table>
        <tr><th>Property</th><th>Buyer</th><th>Date & Time</th><th>Agent</th><th>Status</th></tr>
        <tr><td>8 Pine Ridge</td><td>Martinez, R.</td><td>Sat 2:00 PM</td><td>Sayan</td><td><span class="badge-pill badge-blue">Confirmed</span></td></tr>
        <tr><td>33 Birch Lane</td><td>Patel Family</td><td>Sun 11:00 AM</td><td>Sayan</td><td><span class="badge-pill badge-orange">Pending</span></td></tr>
      </table></div>
    </div>
  </div>
</div>
{_FOOTER_HTML.format(company=company, calendly=config.CALENDLY_MEETING_LINK)}
</body></html>"""


def _ecommerce_template(company: str) -> str:
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{company} — Ops Dashboard Preview</title>
<style>{_BASE_CSS}</style></head><body>
<div class="topbar">
  <div class="logo">{company} <span>Ops</span></div>
  <div class="badge">PREVIEW BUILD</div>
</div>
<div class="hero">
  <h1><span>{company}</span> Unified Commerce Dashboard</h1>
  <p>Orders, inventory, returns, and customer data — all channels in one place, no more switching between Shopify, email, and spreadsheets.</p>
  <div class="cta">
    <a href="{config.CALENDLY_MEETING_LINK}" class="btn btn-primary" target="_blank">Book a Call to Build This</a>
    <a href="https://codevisionaryservices.com/portfolio" class="btn btn-secondary" target="_blank">See Our Work</a>
  </div>
</div>
<div class="dashboard">
  <div class="sidebar">
    <div class="sidebar-section">Operations</div>
    <div class="sidebar-item active"><span class="icon">📦</span> Orders</div>
    <div class="sidebar-item"><span class="icon">🏭</span> Inventory</div>
    <div class="sidebar-item"><span class="icon">↩️</span> Returns</div>
    <div class="sidebar-section">Customers</div>
    <div class="sidebar-item"><span class="icon">👥</span> Customer List</div>
    <div class="sidebar-item"><span class="icon">⭐</span> VIP Buyers</div>
    <div class="sidebar-item"><span class="icon">📣</span> Campaigns</div>
    <div class="sidebar-section">Analytics</div>
    <div class="sidebar-item"><span class="icon">📊</span> Revenue</div>
  </div>
  <div class="content">
    <div class="stats">
      <div class="stat-card"><div class="stat-label">Orders Today</div><div class="stat-value">142</div><div class="stat-delta">↑ 22% vs yesterday</div></div>
      <div class="stat-card"><div class="stat-label">Revenue Today</div><div class="stat-value">$8,340</div><div class="stat-delta">↑ 15% vs yesterday</div></div>
      <div class="stat-card"><div class="stat-label">Pending Dispatch</div><div class="stat-value">38</div><div class="stat-delta" style="color:#c45c00">6 overdue</div></div>
      <div class="stat-card"><div class="stat-label">Return Rate</div><div class="stat-value">3.2%</div><div class="stat-delta">↓ 0.8% this week</div></div>
    </div>
    <div class="panel">
      <div class="panel-header"><span class="panel-title">Recent Orders</span><span class="badge-pill badge-blue">Live Feed</span></div>
      <div class="panel-body"><table>
        <tr><th>Order ID</th><th>Customer</th><th>Items</th><th>Value</th><th>Status</th></tr>
        <tr><td>#10482</td><td>Priya Sharma</td><td>3</td><td>$124.00</td><td><span class="badge-pill badge-green">Dispatched</span></td></tr>
        <tr><td>#10481</td><td>Alex Turner</td><td>1</td><td>$49.99</td><td><span class="badge-pill badge-blue">Processing</span></td></tr>
        <tr><td>#10480</td><td>Li Wei</td><td>5</td><td>$310.50</td><td><span class="badge-pill badge-orange">Pending</span></td></tr>
        <tr><td>#10479</td><td>Sarah M.</td><td>2</td><td>$88.00</td><td><span class="badge-pill badge-green">Delivered</span></td></tr>
      </table></div>
    </div>
    <div class="panel">
      <div class="panel-header"><span class="panel-title">Low Stock Alerts</span></div>
      <div class="panel-body"><table>
        <tr><th>Product</th><th>SKU</th><th>Stock</th><th>Reorder Point</th><th>Action</th></tr>
        <tr><td>Blue Hoodie (L)</td><td>BH-L-001</td><td>4</td><td>10</td><td><span class="badge-pill badge-orange">Reorder Now</span></td></tr>
        <tr><td>Canvas Tote</td><td>CT-STD</td><td>2</td><td>15</td><td><span class="badge-pill badge-orange">Reorder Now</span></td></tr>
      </table></div>
    </div>
  </div>
</div>
{_FOOTER_HTML.format(company=company, calendly=config.CALENDLY_MEETING_LINK)}
</body></html>"""


def _generic_template(company: str, industry: str) -> str:
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{company} — Custom CRM Preview</title>
<style>{_BASE_CSS}</style></head><body>
<div class="topbar">
  <div class="logo">{company} <span>Hub</span></div>
  <div class="badge">PREVIEW BUILD</div>
</div>
<div class="hero">
  <h1>A Custom CRM Built for <span>{company}</span></h1>
  <p>This is a preview of how a purpose-built CRM for your {industry} business could look — your workflow, your data, your way.</p>
  <div class="cta">
    <a href="{config.CALENDLY_MEETING_LINK}" class="btn btn-primary" target="_blank">Book a Call to Build This</a>
    <a href="https://codevisionaryservices.com/portfolio" class="btn btn-secondary" target="_blank">See Our Work</a>
  </div>
</div>
<div class="dashboard">
  <div class="sidebar">
    <div class="sidebar-section">CRM</div>
    <div class="sidebar-item active"><span class="icon">📊</span> Dashboard</div>
    <div class="sidebar-item"><span class="icon">👥</span> Contacts</div>
    <div class="sidebar-item"><span class="icon">💼</span> Deals</div>
    <div class="sidebar-section">Operations</div>
    <div class="sidebar-item"><span class="icon">📋</span> Tasks</div>
    <div class="sidebar-item"><span class="icon">📅</span> Calendar</div>
    <div class="sidebar-item"><span class="icon">📣</span> Campaigns</div>
    <div class="sidebar-section">Reports</div>
    <div class="sidebar-item"><span class="icon">📈</span> Analytics</div>
  </div>
  <div class="content">
    <div class="stats">
      <div class="stat-card"><div class="stat-label">Active Contacts</div><div class="stat-value">1,240</div><div class="stat-delta">↑ 48 this week</div></div>
      <div class="stat-card"><div class="stat-label">Open Deals</div><div class="stat-value">34</div><div class="stat-delta">↑ 6 new this month</div></div>
      <div class="stat-card"><div class="stat-label">Pipeline Value</div><div class="stat-value">$280K</div><div class="stat-delta">On track</div></div>
      <div class="stat-card"><div class="stat-label">Tasks Due Today</div><div class="stat-value">12</div><div class="stat-delta" style="color:#c45c00">3 overdue</div></div>
    </div>
    <div class="panel">
      <div class="panel-header"><span class="panel-title">Deal Pipeline</span><span class="badge-pill badge-blue">34 Open</span></div>
      <div class="panel-body"><table>
        <tr><th>Company</th><th>Contact</th><th>Value</th><th>Stage</th><th>Close Date</th></tr>
        <tr><td>Acme Ltd</td><td>Jane D.</td><td>$24,000</td><td><span class="badge-pill badge-green">Proposal Sent</span></td><td>Dec 30</td></tr>
        <tr><td>TechCorp</td><td>Mark S.</td><td>$8,500</td><td><span class="badge-pill badge-blue">Discovery</span></td><td>Jan 15</td></tr>
        <tr><td>StartUp Co</td><td>Priya K.</td><td>$42,000</td><td><span class="badge-pill badge-orange">Negotiation</span></td><td>Jan 5</td></tr>
        <tr><td>GrowCo</td><td>Tom B.</td><td>$12,000</td><td><span class="badge-pill badge-grey">New Lead</span></td><td>TBD</td></tr>
      </table></div>
    </div>
    <div class="panel">
      <div class="panel-header"><span class="panel-title">Tasks Due Today</span></div>
      <div class="panel-body"><table>
        <tr><th>Task</th><th>Contact</th><th>Priority</th><th>Status</th></tr>
        <tr><td>Follow up on proposal</td><td>Jane D. (Acme)</td><td><span class="badge-pill badge-orange">High</span></td><td>Pending</td></tr>
        <tr><td>Send case studies</td><td>Priya K.</td><td><span class="badge-pill badge-blue">Medium</span></td><td>Pending</td></tr>
        <tr><td>Schedule demo call</td><td>Tom B.</td><td><span class="badge-pill badge-grey">Normal</span></td><td>Pending</td></tr>
      </table></div>
    </div>
  </div>
</div>
{_FOOTER_HTML.format(company=company, calendly=config.CALENDLY_MEETING_LINK)}
</body></html>"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def _pick_template(company: str, industry: str) -> str:
    ind = industry.lower()
    if any(k in ind for k in ["real estate", "realty", "property", "housing", "interior"]):
        return _realestate_template(company)
    if any(k in ind for k in ["ecommerce", "e-commerce", "retail", "shop", "store", "clothing", "jewellery", "furniture"]):
        return _ecommerce_template(company)
    if any(k in ind for k in ["saas", "software", "tech", "crm", "startup", "app", "manufacturing", "ca", "lawyer"]):
        return _saas_template(company)
    # Default for local service businesses (restaurants, salons, clinics, etc.)
    return _generic_template(company, industry)


def _slug(company: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", company.lower()).strip("-")


def generate_demo(lead: dict) -> str:
    """
    Generate a personalized demo HTML page for this lead.
    Saves to docs/demos/<slug>.html and returns the GitHub Pages URL.
    """
    company = lead.get("company") or "Your Company"
    industry = lead.get("industry") or ""
    slug = _slug(company)
    html = _pick_template(company, industry)

    os.makedirs(DEMOS_DIR, exist_ok=True)
    filepath = os.path.join(DEMOS_DIR, f"{slug}.html")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)

    logger.info(f"Demo generated: {filepath}")
    return f"{GITHUB_PAGES_BASE}/{slug}.html"


def publish_demos() -> bool:
    """
    Commit and push any new/updated demo files to GitHub so Pages serves them.
    Returns True on success.
    """
    repo_root = os.path.join(os.path.dirname(__file__), "..")
    try:
        subprocess.run(["git", "add", "docs/demos/"], cwd=repo_root, check=True, capture_output=True)
        result = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=repo_root, capture_output=True)
        if result.returncode == 0:
            logger.info("No new demos to publish.")
            return True
        subprocess.run(
            ["git", "commit", "-m", "auto: publish personalized demo pages"],
            cwd=repo_root, check=True, capture_output=True,
        )
        subprocess.run(["git", "push", "origin", "main"], cwd=repo_root, check=True, capture_output=True)
        logger.info("Demo pages pushed to GitHub Pages.")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to publish demos: {e}")
        return False
