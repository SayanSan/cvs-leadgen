"""
CVS LeadGen — Web Dashboard
FastAPI backend serving a full management UI.
"""

import json
import logging
import subprocess
import sys
import os
from datetime import datetime

from fastapi import FastAPI, BackgroundTasks, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from tools.db_tools import get_db, init_db
from agents.scout_agent import GOOGLE_MAPS_QUERIES, LINKEDIN_SEARCH_QUERIES

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="CVS LeadGen Dashboard")

@app.on_event("startup")
def startup():
    os.makedirs("data", exist_ok=True)
    init_db()

# Serve demo pages as static files
docs_path = os.path.join(os.path.dirname(__file__), "docs")
if os.path.exists(docs_path):
    app.mount("/demos", StaticFiles(directory=os.path.join(docs_path, "demos"), html=True), name="demos")

# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def get_stats() -> dict:
    conn = get_db()
    total     = conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
    new       = conn.execute("SELECT COUNT(*) FROM leads WHERE status='new'").fetchone()[0]
    emailed   = conn.execute("SELECT COUNT(*) FROM leads WHERE status='emailed'").fetchone()[0]
    replied   = conn.execute("SELECT COUNT(*) FROM leads WHERE status='replied'").fetchone()[0]
    meetings  = conn.execute("SELECT COUNT(*) FROM leads WHERE status='meeting_booked'").fetchone()[0]
    closed    = conn.execute("SELECT COUNT(*) FROM leads WHERE status='closed'").fetchone()[0]
    unsub     = conn.execute("SELECT COUNT(*) FROM leads WHERE status='unsubscribed'").fetchone()[0]
    conn.close()
    return {
        "total": total, "new": new, "emailed": emailed,
        "replied": replied, "meetings": meetings,
        "closed": closed, "unsubscribed": unsub,
    }


def get_leads(status: str = None, limit: int = 200) -> list[dict]:
    conn = get_db()
    if status and status != "all":
        rows = conn.execute(
            "SELECT * FROM leads WHERE status=? ORDER BY created_at DESC LIMIT ?",
            (status, limit)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM leads ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ---------------------------------------------------------------------------
# Agent runner (non-blocking background task)
# ---------------------------------------------------------------------------

_agent_logs: list[str] = []

def _run_agent(agent_name: str, dry_run: bool = False, batch_offset: int = 0):
    _agent_logs.clear()
    cmd = [sys.executable, "-u", "main.py", agent_name]
    if dry_run:
        cmd.append("--dry-run")
    if agent_name == "scout" and batch_offset:
        cmd += ["--batch-offset", str(batch_offset)]
    _agent_logs.append(f"[{datetime.utcnow().strftime('%H:%M:%S')}] Starting {agent_name}...")
    try:
        env = {**os.environ, "PYTHONUNBUFFERED": "1"}
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, cwd=os.path.dirname(__file__), env=env
        )
        for line in proc.stdout:
            line = line.rstrip()
            if line:
                _agent_logs.append(line)
        proc.wait()
        _agent_logs.append(f"[{datetime.utcnow().strftime('%H:%M:%S')}] {agent_name} finished.")
    except Exception as e:
        _agent_logs.append(f"ERROR: {e}")

# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------

@app.get("/api/stats")
def api_stats():
    return get_stats()

@app.get("/api/leads")
def api_leads(status: str = "all", limit: int = 200):
    return get_leads(status, limit)

@app.post("/api/run/{agent_name}")
def api_run_agent(agent_name: str, background_tasks: BackgroundTasks, dry_run: bool = False, batch_offset: int = 0):
    if agent_name not in ("scout", "outreach", "sales", "followups"):
        return JSONResponse({"error": "Unknown agent"}, status_code=400)
    background_tasks.add_task(_run_agent, agent_name, dry_run, batch_offset)
    return {"status": "started", "agent": agent_name, "batch_offset": batch_offset}

@app.get("/api/logs")
def api_logs():
    return {"logs": list(_agent_logs)}

# ---------------------------------------------------------------------------
# Scout query config — persisted in data/scout_queries.json
# ---------------------------------------------------------------------------

_QUERIES_FILE = os.path.join(os.path.dirname(__file__), "data", "scout_queries.json")

def _load_queries() -> dict:
    if os.path.exists(_QUERIES_FILE):
        with open(_QUERIES_FILE) as f:
            return json.load(f)
    return {
        "google_maps": [{"query": q, "location": loc} for q, loc in GOOGLE_MAPS_QUERIES],
        "linkedin": list(LINKEDIN_SEARCH_QUERIES),
    }

def _save_queries(data: dict):
    os.makedirs(os.path.dirname(_QUERIES_FILE), exist_ok=True)
    with open(_QUERIES_FILE, "w") as f:
        json.dump(data, f, indent=2)

@app.get("/api/queries")
def api_get_queries():
    return _load_queries()

@app.post("/api/queries")
async def api_save_queries(request: Request):
    data = await request.json()
    _save_queries(data)
    return {"status": "saved"}

@app.post("/api/queries/reset")
def api_reset_queries():
    defaults = {
        "google_maps": [{"query": q, "location": loc} for q, loc in GOOGLE_MAPS_QUERIES],
        "linkedin": list(LINKEDIN_SEARCH_QUERIES),
    }
    _save_queries(defaults)
    return defaults

# ---------------------------------------------------------------------------
# Main UI
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def dashboard():
    return HTMLResponse(DASHBOARD_HTML)


DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>CVS LeadGen Dashboard</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Segoe UI', Arial, sans-serif; background: #f0f2f5; color: #1a1a2e; }

/* Topbar */
.topbar { background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); color: #fff; padding: 0 32px; height: 60px; display: flex; align-items: center; justify-content: space-between; position: sticky; top: 0; z-index: 100; box-shadow: 0 2px 12px rgba(0,0,0,0.3); }
.logo { font-size: 18px; font-weight: 700; letter-spacing: 0.5px; }
.logo span { color: #00d4ff; }
.topbar-right { display: flex; align-items: center; gap: 16px; }
.status-dot { width: 8px; height: 8px; border-radius: 50%; background: #00b359; display: inline-block; margin-right: 6px; animation: pulse 2s infinite; }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }
.topbar-label { font-size: 13px; color: #aaa; }

/* Layout */
.layout { display: grid; grid-template-columns: 220px 1fr; min-height: calc(100vh - 60px); }

/* Sidebar */
.sidebar { background: #fff; border-right: 1px solid #e8eaf0; padding: 20px 0; }
.nav-section { padding: 6px 16px 4px; font-size: 11px; font-weight: 700; color: #999; text-transform: uppercase; letter-spacing: 1px; margin-top: 12px; }
.nav-item { padding: 10px 20px; font-size: 14px; color: #555; cursor: pointer; display: flex; align-items: center; gap: 10px; border-radius: 0 8px 8px 0; margin-right: 12px; transition: all 0.15s; }
.nav-item:hover { background: #f0f2f5; color: #1a1a2e; }
.nav-item.active { background: #eff4ff; color: #0066ff; font-weight: 600; }
.nav-item .icon { font-size: 16px; width: 20px; text-align: center; }
.nav-badge { margin-left: auto; background: #0066ff; color: #fff; font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 20px; }

/* Main content */
.main { padding: 28px; overflow-y: auto; }
.page { display: none; }
.page.active { display: block; }
.page-title { font-size: 22px; font-weight: 700; margin-bottom: 20px; }

/* Stats grid */
.stats { display: grid; grid-template-columns: repeat(6, 1fr); gap: 14px; margin-bottom: 24px; }
.stat-card { background: #fff; padding: 18px; border-radius: 12px; border: 1px solid #e8eaf0; transition: box-shadow 0.2s; cursor: pointer; }
.stat-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.08); }
.stat-card.active-filter { border-color: #0066ff; box-shadow: 0 0 0 2px #ddeeff; }
.stat-label { font-size: 11px; color: #999; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; }
.stat-value { font-size: 28px; font-weight: 700; color: #1a1a2e; }
.stat-sub { font-size: 12px; color: #aaa; margin-top: 4px; }

/* Agent controls */
.agent-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 24px; }
.agent-card { background: #fff; border-radius: 12px; border: 1px solid #e8eaf0; padding: 20px; }
.agent-name { font-size: 15px; font-weight: 600; margin-bottom: 6px; }
.agent-desc { font-size: 13px; color: #888; margin-bottom: 14px; line-height: 1.5; }
.btn { padding: 9px 18px; border-radius: 7px; font-size: 13px; font-weight: 600; cursor: pointer; border: none; transition: all 0.15s; display: inline-flex; align-items: center; gap: 6px; }
.btn-primary { background: #0066ff; color: #fff; }
.btn-primary:hover { background: #0052cc; }
.btn-outline { background: #fff; color: #555; border: 1px solid #dde1ea; }
.btn-outline:hover { background: #f0f2f5; }
.btn-danger { background: #fff0f0; color: #cc0000; border: 1px solid #ffd0d0; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-sm { padding: 5px 12px; font-size: 12px; }

/* Leads table */
.panel { background: #fff; border-radius: 12px; border: 1px solid #e8eaf0; margin-bottom: 20px; overflow: hidden; }
.panel-header { padding: 16px 20px; border-bottom: 1px solid #e8eaf0; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px; }
.panel-title { font-size: 15px; font-weight: 600; }
.filter-row { display: flex; gap: 8px; flex-wrap: wrap; }
.filter-btn { padding: 5px 14px; border-radius: 20px; font-size: 12px; font-weight: 600; border: 1px solid #dde1ea; background: #fff; cursor: pointer; transition: all 0.15s; }
.filter-btn.active, .filter-btn:hover { background: #0066ff; color: #fff; border-color: #0066ff; }
.search-input { padding: 7px 14px; border-radius: 7px; border: 1px solid #dde1ea; font-size: 13px; width: 220px; outline: none; }
.search-input:focus { border-color: #0066ff; }
table { width: 100%; border-collapse: collapse; }
th { padding: 10px 16px; text-align: left; font-size: 11px; font-weight: 700; color: #999; text-transform: uppercase; letter-spacing: 0.5px; background: #f8f9fc; white-space: nowrap; }
td { padding: 12px 16px; font-size: 13px; border-top: 1px solid #f0f2f5; color: #333; max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
tr:hover td { background: #f8f9fc; }
.badge { padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 700; white-space: nowrap; }
.badge-new { background: #f0f2f5; color: #555; }
.badge-emailed { background: #ddeeff; color: #004ecc; }
.badge-replied { background: #d4f5e2; color: #007a38; }
.badge-meeting { background: #f0e6ff; color: #6600cc; }
.badge-closed { background: #1a1a2e; color: #fff; }
.badge-unsub { background: #fff0f0; color: #cc0000; }
.badge-notint { background: #fff8e0; color: #a06000; }
.demo-link { color: #0066ff; text-decoration: none; font-weight: 600; }
.demo-link:hover { text-decoration: underline; }
.no-leads { text-align: center; padding: 48px; color: #aaa; font-size: 15px; }

/* Log console */
.log-console { background: #0d1117; border-radius: 10px; padding: 20px; font-family: 'SF Mono', 'Fira Code', monospace; font-size: 12px; color: #7ee787; min-height: 200px; max-height: 360px; overflow-y: auto; line-height: 1.7; }
.log-console .log-line { margin: 0; }
.log-console .log-error { color: #f85149; }
.log-console .log-warn { color: #e3b341; }

/* Pipeline visual */
.pipeline { display: flex; align-items: center; gap: 0; margin-bottom: 24px; overflow-x: auto; }
.pipe-stage { background: #fff; border: 1px solid #e8eaf0; padding: 16px 24px; text-align: center; flex: 1; min-width: 110px; }
.pipe-stage:first-child { border-radius: 12px 0 0 12px; }
.pipe-stage:last-child { border-radius: 0 12px 12px 0; }
.pipe-arrow { color: #dde1ea; font-size: 20px; flex-shrink: 0; }
.pipe-count { font-size: 26px; font-weight: 700; }
.pipe-label { font-size: 11px; color: #999; text-transform: uppercase; letter-spacing: 0.5px; margin-top: 4px; }
.pipe-new .pipe-count { color: #555; }
.pipe-emailed .pipe-count { color: #0066ff; }
.pipe-replied .pipe-count { color: #00b359; }
.pipe-meeting .pipe-count { color: #6600cc; }
.pipe-closed .pipe-count { color: #1a1a2e; }

/* Modal */
.modal-overlay { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.5); z-index: 200; align-items: center; justify-content: center; }
.modal-overlay.open { display: flex; }
.modal { background: #fff; border-radius: 16px; padding: 28px; max-width: 560px; width: 90%; max-height: 80vh; overflow-y: auto; }
.modal-title { font-size: 18px; font-weight: 700; margin-bottom: 16px; }
.modal-field { margin-bottom: 12px; }
.modal-label { font-size: 11px; font-weight: 700; color: #999; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; }
.modal-value { font-size: 14px; color: #333; }
.modal-close { float: right; background: none; border: none; font-size: 20px; cursor: pointer; color: #999; }

/* Toast */
.toast { position: fixed; bottom: 24px; right: 24px; background: #1a1a2e; color: #fff; padding: 12px 20px; border-radius: 10px; font-size: 14px; z-index: 300; transform: translateY(80px); opacity: 0; transition: all 0.3s; }
.toast.show { transform: translateY(0); opacity: 1; }

/* Responsive */
@media (max-width: 900px) {
  .stats { grid-template-columns: repeat(3, 1fr); }
  .agent-grid { grid-template-columns: repeat(2, 1fr); }
}
</style>
</head>
<body>

<div class="topbar">
  <div class="logo">Code Visionary <span>LeadGen</span></div>
  <div class="topbar-right">
    <span><span class="status-dot"></span><span class="topbar-label">Live</span></span>
    <span class="topbar-label" id="last-updated">—</span>
  </div>
</div>

<div class="layout">
  <div class="sidebar">
    <div class="nav-section">Main</div>
    <div class="nav-item active" onclick="showPage('dashboard')"><span class="icon">📊</span> Dashboard</div>
    <div class="nav-item" onclick="showPage('leads')"><span class="icon">👥</span> Leads <span class="nav-badge" id="nav-total">—</span></div>
    <div class="nav-item" onclick="showPage('agents')"><span class="icon">🤖</span> Run Agents</div>
    <div class="nav-item" onclick="showPage('settings')"><span class="icon">⚙️</span> Settings</div>
    <div class="nav-section">Pipeline</div>
    <div class="nav-item" onclick="showPage('leads'); filterLeads('new')"><span class="icon">🆕</span> New</div>
    <div class="nav-item" onclick="showPage('leads'); filterLeads('emailed')"><span class="icon">📧</span> Emailed</div>
    <div class="nav-item" onclick="showPage('leads'); filterLeads('replied')"><span class="icon">💬</span> Replied</div>
    <div class="nav-item" onclick="showPage('leads'); filterLeads('meeting_booked')"><span class="icon">📅</span> Meetings</div>
    <div class="nav-item" onclick="showPage('leads'); filterLeads('closed')"><span class="icon">✅</span> Closed</div>
  </div>

  <div class="main">

    <!-- DASHBOARD PAGE -->
    <div class="page active" id="page-dashboard">
      <div class="page-title">Dashboard</div>

      <div class="stats">
        <div class="stat-card" onclick="showPage('leads'); filterLeads('all')">
          <div class="stat-label">Total Leads</div>
          <div class="stat-value" id="stat-total">—</div>
          <div class="stat-sub">All sources</div>
        </div>
        <div class="stat-card" onclick="showPage('leads'); filterLeads('new')">
          <div class="stat-label">New</div>
          <div class="stat-value" id="stat-new">—</div>
          <div class="stat-sub">Awaiting outreach</div>
        </div>
        <div class="stat-card" onclick="showPage('leads'); filterLeads('emailed')">
          <div class="stat-label">Emailed</div>
          <div class="stat-value" id="stat-emailed">—</div>
          <div class="stat-sub">Demo sent</div>
        </div>
        <div class="stat-card" onclick="showPage('leads'); filterLeads('replied')">
          <div class="stat-label">Replied</div>
          <div class="stat-value" id="stat-replied">—</div>
          <div class="stat-sub">Engaged</div>
        </div>
        <div class="stat-card" onclick="showPage('leads'); filterLeads('meeting_booked')">
          <div class="stat-label">Meetings</div>
          <div class="stat-value" id="stat-meetings">—</div>
          <div class="stat-sub">Booked</div>
        </div>
        <div class="stat-card" onclick="showPage('leads'); filterLeads('closed')">
          <div class="stat-label">Closed</div>
          <div class="stat-value" id="stat-closed">—</div>
          <div class="stat-sub">Won</div>
        </div>
      </div>

      <div class="pipeline">
        <div class="pipe-stage pipe-new"><div class="pipe-count" id="pipe-new">—</div><div class="pipe-label">New</div></div>
        <div class="pipe-arrow">›</div>
        <div class="pipe-stage pipe-emailed"><div class="pipe-count" id="pipe-emailed">—</div><div class="pipe-label">Emailed</div></div>
        <div class="pipe-arrow">›</div>
        <div class="pipe-stage pipe-replied"><div class="pipe-count" id="pipe-replied">—</div><div class="pipe-label">Replied</div></div>
        <div class="pipe-arrow">›</div>
        <div class="pipe-stage pipe-meeting"><div class="pipe-count" id="pipe-meeting">—</div><div class="pipe-label">Meeting</div></div>
        <div class="pipe-arrow">›</div>
        <div class="pipe-stage pipe-closed"><div class="pipe-count" id="pipe-closed">—</div><div class="pipe-label">Closed</div></div>
      </div>

      <div class="panel">
        <div class="panel-header"><span class="panel-title">Recent Leads</span></div>
        <table>
          <thead><tr><th>Company</th><th>Name</th><th>Title</th><th>Source</th><th>Status</th><th>Demo</th></tr></thead>
          <tbody id="recent-leads-body"></tbody>
        </table>
      </div>
    </div>

    <!-- LEADS PAGE -->
    <div class="page" id="page-leads">
      <div class="page-title">Leads</div>
      <div class="panel">
        <div class="panel-header">
          <span class="panel-title" id="leads-panel-title">All Leads</span>
          <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;">
            <input class="search-input" id="search-input" placeholder="Search company, name, email..." oninput="renderLeadsTable()">
            <div class="filter-row" id="filter-row">
              <button class="filter-btn active" onclick="filterLeads('all')">All</button>
              <button class="filter-btn" onclick="filterLeads('new')">New</button>
              <button class="filter-btn" onclick="filterLeads('emailed')">Emailed</button>
              <button class="filter-btn" onclick="filterLeads('replied')">Replied</button>
              <button class="filter-btn" onclick="filterLeads('meeting_booked')">Meeting</button>
              <button class="filter-btn" onclick="filterLeads('closed')">Closed</button>
            </div>
          </div>
        </div>
        <table>
          <thead><tr><th>Company</th><th>Name</th><th>Title</th><th>Email</th><th>Source</th><th>Industry</th><th>Status</th><th>Demo</th></tr></thead>
          <tbody id="leads-body"></tbody>
        </table>
      </div>
    </div>

    <!-- SETTINGS PAGE -->
    <div class="page" id="page-settings">
      <div class="page-title">Settings — Scout Queries</div>

      <div class="panel" style="margin-bottom:20px;">
        <div class="panel-header">
          <span class="panel-title">Google Maps Queries</span>
          <button class="btn btn-outline btn-sm" onclick="addGoogleRow()">+ Add Row</button>
        </div>
        <div style="padding:16px;">
          <p style="font-size:13px;color:#888;margin-bottom:12px;">Each row is one search the Scout runs. <b>Query</b> = what to search, <b>Location</b> = which city.</p>
          <table style="width:100%;border-collapse:collapse;" id="gmap-table">
            <thead><tr>
              <th style="text-align:left;padding:8px;font-size:11px;color:#999;text-transform:uppercase;">Query</th>
              <th style="text-align:left;padding:8px;font-size:11px;color:#999;text-transform:uppercase;">Location</th>
              <th style="width:40px;"></th>
            </tr></thead>
            <tbody id="gmap-body"></tbody>
          </table>
        </div>
      </div>

      <div class="panel" style="margin-bottom:20px;">
        <div class="panel-header">
          <span class="panel-title">LinkedIn Search Queries</span>
          <button class="btn btn-outline btn-sm" onclick="addLinkedInRow()">+ Add Row</button>
        </div>
        <div style="padding:16px;">
          <p style="font-size:13px;color:#888;margin-bottom:12px;">Each row is a LinkedIn people search query. Target decision-makers and business owners.</p>
          <div id="linkedin-list"></div>
        </div>
      </div>

      <div style="display:flex;gap:12px;margin-bottom:40px;">
        <button class="btn btn-primary" onclick="saveQueries()">💾 Save Changes</button>
        <button class="btn btn-outline" onclick="resetQueries()">↺ Reset to Defaults</button>
      </div>
    </div>

    <!-- AGENTS PAGE -->
    <div class="page" id="page-agents">
      <div class="page-title">Run Agents</div>
      <div class="agent-grid">
        <div class="agent-card">
          <div class="agent-name">🔍 Scout Agent</div>
          <div class="agent-desc">Scrapes Google Maps for new leads — runs 5 queries per batch (~5 min each). Run batches in sequence to cover all queries.</div>
          <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px;">
            <button class="btn btn-primary btn-sm" onclick="runScoutBatch(0)">Batch 1–5</button>
            <button class="btn btn-primary btn-sm" onclick="runScoutBatch(5)">Batch 6–10</button>
            <button class="btn btn-primary btn-sm" onclick="runScoutBatch(10)">Batch 11–15</button>
            <button class="btn btn-primary btn-sm" onclick="runScoutBatch(15)">Batch 16–20</button>
            <button class="btn btn-primary btn-sm" onclick="runScoutBatch(20)">Batch 21–25</button>
            <button class="btn btn-primary btn-sm" onclick="runScoutBatch(25)">Batch 26–30</button>
          </div>
          <button class="btn btn-outline btn-sm" onclick="runAgent('scout', true)">Dry Run</button>
        </div>
        <div class="agent-card">
          <div class="agent-name">📧 Outreach Agent</div>
          <div class="agent-desc">Generates personalized demo pages and sends initial emails to all new leads.</div>
          <div style="display:flex;gap:8px;">
            <button class="btn btn-primary" onclick="runAgent('outreach')">Run Outreach</button>
            <button class="btn btn-outline btn-sm" onclick="runAgent('outreach', true)">Dry Run</button>
          </div>
        </div>
        <div class="agent-card">
          <div class="agent-name">💬 Sales Agent</div>
          <div class="agent-desc">Monitors inbox for replies, classifies intent, and responds with demo links and Calendly.</div>
          <div style="display:flex;gap:8px;">
            <button class="btn btn-primary" onclick="runAgent('sales')">Run Sales</button>
            <button class="btn btn-outline btn-sm" onclick="runAgent('sales', true)">Dry Run</button>
          </div>
        </div>
        <div class="agent-card">
          <div class="agent-name">🔁 Follow-ups</div>
          <div class="agent-desc">Sends follow-up emails to leads that were emailed 3+ days ago with no reply.</div>
          <div style="display:flex;gap:8px;">
            <button class="btn btn-primary" onclick="runAgent('followups')">Run Follow-ups</button>
            <button class="btn btn-outline btn-sm" onclick="runAgent('followups', true)">Dry Run</button>
          </div>
        </div>
      </div>

      <div class="panel">
        <div class="panel-header">
          <span class="panel-title">Agent Logs</span>
          <button class="btn btn-outline btn-sm" onclick="clearLogs()">Clear</button>
        </div>
        <div style="padding:16px;">
          <div class="log-console" id="log-console"><p class="log-line" style="color:#555">No agent running. Click a button above to start.</p></div>
        </div>
      </div>
    </div>

  </div>
</div>

<!-- Lead detail modal -->
<div class="modal-overlay" id="lead-modal" onclick="closeModal(event)">
  <div class="modal">
    <button class="modal-close" onclick="document.getElementById('lead-modal').classList.remove('open')">×</button>
    <div class="modal-title" id="modal-company">—</div>
    <div id="modal-fields"></div>
  </div>
</div>

<div class="toast" id="toast"></div>

<script>
let allLeads = [];
let currentFilter = 'all';
let agentRunning = false;
let logInterval = null;

// ---------------------------------------------------------------------------
// Navigation
// ---------------------------------------------------------------------------
function showPage(name) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.getElementById('page-' + name).classList.add('active');
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  const navMap = {dashboard: 0, leads: 1, agents: 2, settings: 3};
  if (navMap[name] !== undefined) document.querySelectorAll('.nav-item')[navMap[name]].classList.add('active');
  if (name === 'leads') loadLeads();
  if (name === 'settings') loadSettings();
}

// ---------------------------------------------------------------------------
// Stats
// ---------------------------------------------------------------------------
async function loadStats() {
  const data = await fetch('/api/stats').then(r => r.json());
  document.getElementById('stat-total').textContent = data.total;
  document.getElementById('stat-new').textContent = data.new;
  document.getElementById('stat-emailed').textContent = data.emailed;
  document.getElementById('stat-replied').textContent = data.replied;
  document.getElementById('stat-meetings').textContent = data.meetings;
  document.getElementById('stat-closed').textContent = data.closed;
  document.getElementById('pipe-new').textContent = data.new;
  document.getElementById('pipe-emailed').textContent = data.emailed;
  document.getElementById('pipe-replied').textContent = data.replied;
  document.getElementById('pipe-meeting').textContent = data.meetings;
  document.getElementById('pipe-closed').textContent = data.closed;
  document.getElementById('nav-total').textContent = data.total;
  document.getElementById('last-updated').textContent = 'Updated ' + new Date().toLocaleTimeString();
}

// ---------------------------------------------------------------------------
// Leads
// ---------------------------------------------------------------------------
function statusBadge(s) {
  const map = {
    new: 'badge-new', emailed: 'badge-emailed', replied: 'badge-replied',
    meeting_booked: 'badge-meeting', closed: 'badge-closed',
    unsubscribed: 'badge-unsub', not_interested: 'badge-notint',
  };
  const cls = map[s] || 'badge-new';
  return `<span class="badge ${cls}">${s.replace('_',' ')}</span>`;
}

function demoLink(lead) {
  if (!lead.company) return '—';
  const slug = lead.company.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
  return `<a class="demo-link" href="/demos/${slug}.html" target="_blank">View →</a>`;
}

async function loadLeads() {
  allLeads = await fetch('/api/leads?limit=500').then(r => r.json());
  renderLeadsTable();
  renderRecentLeads();
}

function filterLeads(status) {
  currentFilter = status;
  document.querySelectorAll('.filter-btn').forEach(b => {
    b.classList.toggle('active', b.textContent.toLowerCase().replace(' ','_') === status || (status === 'all' && b.textContent === 'All'));
  });
  renderLeadsTable();
}

function renderLeadsTable() {
  const search = (document.getElementById('search-input')?.value || '').toLowerCase();
  const filtered = allLeads.filter(l => {
    const matchStatus = currentFilter === 'all' || l.status === currentFilter;
    const matchSearch = !search || [l.company, l.name, l.email, l.industry].some(v => (v||'').toLowerCase().includes(search));
    return matchStatus && matchSearch;
  });
  document.getElementById('leads-panel-title').textContent = `${filtered.length} Leads${currentFilter !== 'all' ? ' — ' + currentFilter : ''}`;
  const tbody = document.getElementById('leads-body');
  if (!filtered.length) {
    tbody.innerHTML = '<tr><td colspan="8" class="no-leads">No leads found</td></tr>';
    return;
  }
  tbody.innerHTML = filtered.map(l => `
    <tr onclick="openModal(${l.id})" style="cursor:pointer">
      <td title="${l.company||''}">${l.company||'—'}</td>
      <td>${l.name||'—'}</td>
      <td title="${l.title||''}">${l.title||'—'}</td>
      <td title="${l.email||''}">${l.email||'—'}</td>
      <td>${l.source||'—'}</td>
      <td>${l.industry||'—'}</td>
      <td>${statusBadge(l.status)}</td>
      <td>${demoLink(l)}</td>
    </tr>`).join('');
}

function renderRecentLeads() {
  const recent = allLeads.slice(0, 10);
  const tbody = document.getElementById('recent-leads-body');
  if (!recent.length) {
    tbody.innerHTML = '<tr><td colspan="6" class="no-leads">No leads yet — run the Scout Agent to start</td></tr>';
    return;
  }
  tbody.innerHTML = recent.map(l => `
    <tr onclick="openLead(${l.id})" style="cursor:pointer">
      <td>${l.company||'—'}</td><td>${l.name||'—'}</td>
      <td>${l.title||'—'}</td><td>${l.source||'—'}</td>
      <td>${statusBadge(l.status)}</td><td>${demoLink(l)}</td>
    </tr>`).join('');
}

function openModal(id) {
  const lead = allLeads.find(l => l.id === id);
  if (!lead) return;
  document.getElementById('modal-company').textContent = lead.company || 'Lead Details';
  const slug = (lead.company||'').toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'');
  const fields = [
    ['Name', lead.name], ['Title', lead.title], ['Email', lead.email],
    ['Phone', lead.phone], ['Location', lead.location], ['Industry', lead.industry],
    ['Source', lead.source], ['Status', lead.status], ['Website', lead.website],
    ['LinkedIn', lead.linkedin_url], ['Company Size', lead.company_size],
  ].filter(([,v]) => v);
  document.getElementById('modal-fields').innerHTML = fields.map(([k,v]) => `
    <div class="modal-field"><div class="modal-label">${k}</div><div class="modal-value">${v}</div></div>`).join('') +
    `<div style="margin-top:16px;"><a href="/demos/${slug}.html" target="_blank" class="btn btn-primary">👁 View Personalized Demo</a></div>`;
  document.getElementById('lead-modal').classList.add('open');
}

function closeModal(e) {
  if (e.target.id === 'lead-modal') document.getElementById('lead-modal').classList.remove('open');
}

// ---------------------------------------------------------------------------
// Agent runner
// ---------------------------------------------------------------------------
async function runScoutBatch(offset) {
  if (agentRunning) { showToast('An agent is already running'); return; }
  agentRunning = true;
  showPage('agents');
  document.getElementById('log-console').innerHTML = '';
  showToast(`Starting Scout batch (queries ${offset+1}–${offset+5})...`);
  await fetch(`/api/run/scout?batch_offset=${offset}`, { method: 'POST' });
  logInterval = setInterval(async () => {
    const data = await fetch('/api/logs').then(r => r.json());
    const console_ = document.getElementById('log-console');
    console_.innerHTML = data.logs.map(line => {
      const cls = line.includes('ERROR') ? 'log-error' : line.includes('WARN') ? 'log-warn' : '';
      return `<p class="log-line ${cls}">${line}</p>`;
    }).join('');
    console_.scrollTop = console_.scrollHeight;
    if (data.logs.some(l => l.includes('finished'))) {
      clearInterval(logInterval); agentRunning = false;
      showToast('Scout batch finished'); loadStats(); loadLeads();
    }
  }, 1500);
}

async function runAgent(name, dryRun = false) {
  if (agentRunning) { showToast('An agent is already running'); return; }
  agentRunning = true;
  showPage('agents');
  const console_ = document.getElementById('log-console');
  console_.innerHTML = '';
  showToast(`Starting ${name} agent...`);

  await fetch(`/api/run/${name}?dry_run=${dryRun}`, { method: 'POST' });

  logInterval = setInterval(async () => {
    const data = await fetch('/api/logs').then(r => r.json());
    console_.innerHTML = data.logs.map(line => {
      const cls = line.includes('ERROR') ? 'log-error' : line.includes('WARN') ? 'log-warn' : '';
      return `<p class="log-line ${cls}">${line}</p>`;
    }).join('');
    console_.scrollTop = console_.scrollHeight;

    const done = data.logs.some(l => l.includes('finished'));
    if (done) {
      clearInterval(logInterval);
      agentRunning = false;
      showToast('Agent finished');
      loadStats();
      loadLeads();
    }
  }, 1500);
}

function clearLogs() {
  document.getElementById('log-console').innerHTML = '<p class="log-line" style="color:#555">Logs cleared.</p>';
}

// ---------------------------------------------------------------------------
// Toast
// ---------------------------------------------------------------------------
function showToast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 3000);
}

// ---------------------------------------------------------------------------
// Settings — query editor
// ---------------------------------------------------------------------------
let _queries = { google_maps: [], linkedin: [] };

async function loadSettings() {
  _queries = await fetch('/api/queries').then(r => r.json());
  renderGmapTable();
  renderLinkedInList();
}

function renderGmapTable() {
  const tbody = document.getElementById('gmap-body');
  tbody.innerHTML = _queries.google_maps.map((row, i) => `
    <tr>
      <td style="padding:6px 8px;">
        <input style="width:100%;padding:6px 10px;border:1px solid #dde1ea;border-radius:6px;font-size:13px;"
          value="${row.query}" oninput="_queries.google_maps[${i}].query=this.value">
      </td>
      <td style="padding:6px 8px;">
        <input style="width:100%;padding:6px 10px;border:1px solid #dde1ea;border-radius:6px;font-size:13px;"
          value="${row.location}" oninput="_queries.google_maps[${i}].location=this.value">
      </td>
      <td style="padding:6px 4px;text-align:center;">
        <button onclick="removeGmapRow(${i})" style="background:none;border:none;color:#cc0000;cursor:pointer;font-size:16px;">×</button>
      </td>
    </tr>`).join('');
}

function renderLinkedInList() {
  const el = document.getElementById('linkedin-list');
  el.innerHTML = _queries.linkedin.map((q, i) => `
    <div style="display:flex;gap:8px;margin-bottom:8px;align-items:center;">
      <input style="flex:1;padding:7px 12px;border:1px solid #dde1ea;border-radius:6px;font-size:13px;"
        value="${q}" oninput="_queries.linkedin[${i}]=this.value">
      <button onclick="removeLinkedInRow(${i})" style="background:none;border:none;color:#cc0000;cursor:pointer;font-size:18px;">×</button>
    </div>`).join('');
}

function addGoogleRow() {
  _queries.google_maps.push({ query: '', location: 'Kolkata' });
  renderGmapTable();
}

function removeGmapRow(i) {
  _queries.google_maps.splice(i, 1);
  renderGmapTable();
}

function addLinkedInRow() {
  _queries.linkedin.push('');
  renderLinkedInList();
}

function removeLinkedInRow(i) {
  _queries.linkedin.splice(i, 1);
  renderLinkedInList();
}

async function saveQueries() {
  await fetch('/api/queries', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(_queries)
  });
  showToast('✅ Queries saved — Scout will use these next run');
}

async function resetQueries() {
  if (!confirm('Reset all queries to defaults?')) return;
  const res = await fetch('/api/queries/reset', { method: 'POST' });
  _queries = await res.json();
  renderGmapTable();
  renderLinkedInList();
  showToast('Queries reset to defaults');
}

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------
loadStats();
loadLeads();
setInterval(loadStats, 30000);
</script>
</body>
</html>
"""
