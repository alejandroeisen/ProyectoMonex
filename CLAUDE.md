# Project Context for Claude Code

## What this is
Internal financial dashboard for Intelimed. Replaces an Excel-based workflow so the team can access live market data (stocks, exchange rates, etc.) from outside the office. Not public-facing — authenticated access only.

## Current status
Working dev mockup. Login, sheet selector, data tables with search/sort, and frontend auto-refresh (every 30s) are functional. Sync script reads a local Excel file and writes to PostgreSQL on a loop.

## Hardware setup (decided)
- **Work PC**: Xenith license #1 + Excel. Team uses this for daily work. No scripts run here — untouched.
- **Mini PC** (to be purchased, ~$600 + UPS): Xenith license #2 + Excel + sync script + PostgreSQL + FastAPI. Runs headless 24/7. This is the server AND the data source. Accessible from outside the office.

## The data source
**Metastock Xenith** feeds live RTD data into Excel via a COM add-in. Not a REST API.
- Mini PC runs its own Excel instance with its own Xenith license — fully independent from the work PC
- Sync script reads from the live Excel process on the mini PC via **win32com** (COM automation)
- No network shares, no dependency on the work PC being on
- For dev/testing on Linux: openpyxl reads a static `.xlsx` file as a stand-in

## Architecture
```
[Work PC]                        [Mini PC — dedicated server]
Xenith + Excel                   Xenith + Excel (live RTD data)
Team works here                       |
(independent)                  [sync/excel_sync_windows.py]  ← win32com, reads live Excel
                                      |
                               [PostgreSQL]
                                      |
                               [FastAPI backend]  ← JWT auth
                                      |
                               [React frontend]
                                      ↑
                          [Users, from anywhere, authenticated]
```

## Tech stack
- **Backend**: Python, FastAPI, psycopg2, python-jose (JWT), bcrypt
- **Frontend**: React (Vite), plain CSS
- **Database**: PostgreSQL (JSONB for row data — flexible schema, different headers per sheet)
- **Sync script (dev/Linux)**: `sync/excel_sync.py` — openpyxl, reads static .xlsx
- **Sync script (production/Windows)**: `sync/excel_sync_windows.py` — win32com, reads live Excel — NOT YET BUILT
- **Auth**: JWT tokens stored in localStorage, 8-hour expiry

## Project structure
```
ProyectoIlanErgas/
├── backend/
│   ├── app/
│   │   ├── main.py           ← FastAPI app + CORS + startup
│   │   ├── database.py       ← psycopg2 connection + table init
│   │   ├── auth.py           ← JWT + bcrypt password hashing
│   │   └── routers/
│   │       ├── auth.py       ← POST /auth/login
│   │       └── sheets.py     ← GET /sheets/, GET /sheets/{id}/data
│   ├── init_db.py            ← run once: creates tables + seeds superuser admin
│   ├── requirements.txt
│   └── .env.example          ← copy to .env and fill in credentials
├── sync/
│   ├── excel_sync.py         ← Linux dev: openpyxl on static file. Pass --loop for continuous
│   ├── sync.log              ← rotating log written by excel_sync.py (gitignored)
│   └── excel_sync_windows.py ← Windows prod: win32com on live Excel (NOT YET BUILT)
└── frontend/
    └── src/
        ├── App.jsx            ← auth state, routes between Login and Dashboard
        ├── api.js             ← all fetch calls to backend
        ├── pages/
        │   ├── Login.jsx/css
        │   ├── Dashboard.jsx/css   ← sidebar sheet selector + main content area
        │   ├── AdminPanel.jsx/css  ← user management + sheet permissions (admin only)
        │   └── LogsPanel.jsx/css   ← DB status, sync log tail, sheet counts (admin only)
        └── components/
            └── DataTable.jsx/css   ← table with search filter + column sort
```

## Local dev setup (first time)
```bash
# 1. PostgreSQL — create DB and user
sudo -u postgres psql -c "CREATE USER intelimed WITH PASSWORD 'intelimed123';"
sudo -u postgres psql -c "CREATE DATABASE intelimed_db OWNER intelimed;"

# 2. Backend
cd backend
python3 -m venv venv
venv/bin/pip install -r requirements.txt
cp .env.example .env          # fill in your values
venv/bin/python init_db.py    # creates tables + admin user (admin / admin123)
venv/bin/uvicorn app.main:app --reload

# 3. Sync script (Linux dev)
cd sync
python3 -m venv venv
venv/bin/pip install openpyxl psycopg2-binary python-dotenv
venv/bin/python excel_sync.py ../datos_fake.xlsx         # run once
venv/bin/python excel_sync.py ../datos_fake.xlsx --loop  # run continuously

# 4. Frontend
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

## What's next (not yet built)

### Core / unblocked
- `excel_sync_windows.py` — win32com script for the mini PC (waiting on sheet layout confirmation)
  - Must include: graceful handling of Excel open but Xenith not yet connected (wait, don't write stale data)
  - File-based logging already designed in excel_sync.py — mirror the same pattern
- Dashboard/summary view in the frontend (waiting on contents of their summary sheet)
- **localStorage cache for last-seen sheet data** — so page loads while DB is down still show data
  - ~500KB total for real data (12 sheets, 1500 rows, 10 cols) — fits well within 5MB localStorage limit
  - Write only the active sheet on each successful refresh (~38KB every 5s) — negligible SSD impact

### Done this session (feature/adminPanel branch)
- ✅ Role-based access enforced (admin vs viewer, JWT carries user_id + role)
- ✅ User management UI: Admin tab in sidebar — create/delete users, assign sheet permissions
- ✅ Superuser concept: `is_superuser` flag, default admin is protected from deletion
- ✅ Logs tab: DB status, last sync time, sheet row counts, sync log tail (auto-refreshes 10s)
- ✅ Stale data banner when auto-refresh fails — table stays visible
- ✅ Sidebar retries sheet list every 10s if initial load failed
- ✅ Sync script writes to rotating log file (sync/sync.log)
- ✅ Full test suite: 31 tests across auth, sheets, admin endpoints

### Monitoring / observability
- **RDP remains essential** as fallback for when the URL itself is unreachable (network/power issues)
- Logs tab covers the common cases (DB down, sync stopped, stale data)

### Deployment (when ready)
- Windows setup on mini PC: Task Scheduler auto-start for sync script + backend + PostgreSQL
- Outside access: Dynamic DNS + port forwarding on office router, or WireGuard VPN
- RDP enabled on mini PC during setup (one-time config, documented in handoff)

### Deployment
- Windows setup on mini PC: Task Scheduler auto-start for sync script + backend + PostgreSQL
- Outside access: Dynamic DNS + port forwarding on office router, or WireGuard VPN
- RDP enabled on mini PC during setup (one-time config, documented in handoff)

## Pending decisions / blockers
- **Sheet layout**: pushing client to use one table per sheet (currently multiple tables per sheet — incompatible with current data model)
- **Summary/dashboard sheet**: first sheet is a non-tabular summary — plan is to rebuild it as a proper web dashboard view using aggregated data from the other sheets. Waiting on contents.
- **Outside access method**: dynamic DNS vs VPN — not decided yet

## Key decisions made
- **Mini PC over VPS**: client prefers on-premises. Two Xenith licenses — one for work PC, one for mini PC server.
- **win32com on mini PC**: sync script runs locally on the mini PC, reads its own live Excel instance. Clean — no network shares, no dependency on work PC.
- **JSONB storage**: each row stored as a JSON blob because sheets have different headers. Column list stored separately in `sheets.columns`.
- **No ORM**: raw psycopg2 with RealDictCursor — simple enough that SQLAlchemy would be overhead.
- **bcrypt directly**: passlib was dropped because it breaks with newer bcrypt versions.
- **Keep Excel on work PC untouched**: no scripts, no performance impact on the team's machine.
