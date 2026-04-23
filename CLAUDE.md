# Project Context

## What this is
Internal financial dashboard built as a freelance project. Replaces an Excel-based workflow so the client's team can access live market data (stocks, exchange rates, etc.) from outside the office. Not public-facing — authenticated access only.

## Working instructions for Claude
- Always propose the next step at the end of each response unless told otherwise
- Help architect and diagram when relevant
- Always consider security concerns when building or coding

## Current status
Working dev setup. Login, sheet selector, data tables with search/sort, and frontend auto-refresh (every 30s) are functional. Push script reads live Excel via xlwings and POSTs to FastAPI, which writes to PostgreSQL. Tested end-to-end on Windows.

**Active branch**: `feature/win32com-push` — new push architecture (pending client approval before merging to main).

## Hardware setup (decided)
- **Work PC**: Xenith license + Excel. Team uses this for daily work — they edit the file constantly (adding new rows for trades on different tables). Runs `excel_push.py` silently in the background.
- **Mini PC** (to be purchased, ~$600 + UPS): PostgreSQL + FastAPI + React frontend. Runs headless 24/7. Acts as the server. Does NOT need a Xenith license or Excel installation.

## The data source
**Metastock Xenith** feeds live RTD data into Excel on the Work PC via a COM add-in. The team also edits this file daily — new rows are added to tables for trade entries.

`excel_push.py` runs on the Work PC, reads live in-memory Excel data (not what's saved to disk) via **xlwings**, and POSTs it directly to the Mini PC's FastAPI. This means:
- No file sync needed (no Syncthing, no network shares)
- Data reflects the current in-memory state of Excel, not the last save
- Works whether the Work PC is at the office or at home — just needs internet to reach the Mini PC
- Latency is whatever `PUSH_INTERVAL_SECONDS` is set to (default 60s)

## Architecture
```
[Work PC — office or home]
Xenith + Excel (live RTD + manual edits)
excel_push.py (xlwings reads live memory)
        |
        | HTTP POST + API key
        | (LAN when in office, internet when at home)
        ↓
[Mini PC — office, always on, Tailscale]
POST /internal/push → FastAPI → PostgreSQL
        |
FastAPI serves authenticated endpoints
        |
React frontend (auto-refreshes every 30s)
        ↑
[Users, from anywhere, JWT authenticated]
```

## Tech stack
- **Backend**: Python, FastAPI, psycopg2, python-jose (JWT), bcrypt
- **Frontend**: React (Vite), plain CSS
- **Database**: PostgreSQL (JSONB for row data — flexible schema, different headers per sheet)
- **Push script**: `sync/excel_push.py` — xlwings (live Excel) or openpyxl (--file mode for dev/testing)
- **Connectivity**: Tailscale — Work PC and Mini PC on a private VPN. No port forwarding needed. Works from office and home transparently.
- **Auth**: JWT tokens stored in localStorage, 8-hour expiry
- **Sync API key**: shared secret between push script and backend, compared with `secrets.compare_digest`

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
│   │       ├── sheets.py     ← GET /sheets/, GET /sheets/{id}/data
│   │       └── internal.py   ← POST /internal/push (API key auth, hidden from docs)
│   ├── init_db.py            ← run once: creates tables + seeds admin user (admin/admin123)
│   ├── requirements.txt
│   └── .env.example
├── sync/
│   ├── excel_push.py         ← runs on Work PC. xlwings mode (default) or --file for dev.
│   └── .env.example
├── datos_fake.xlsx            ← static dev/test data
└── frontend/
    └── src/
        ├── App.jsx            ← auth state, routes between Login and Dashboard
        ├── api.js             ← all fetch calls to backend
        ├── pages/
        │   ├── Login.jsx/css
        │   └── Dashboard.jsx/css   ← sidebar sheet selector + main content area
        └── components/
            └── DataTable.jsx/css   ← table with search filter + column sort
```

## Local dev setup (Windows, first time)
```bash
# 1. PostgreSQL — install via winget, then:
& "C:\Program Files\PostgreSQL\17\bin\psql.exe" -U postgres -c "CREATE USER intelimed WITH PASSWORD 'intelimed123';"
& "C:\Program Files\PostgreSQL\17\bin\psql.exe" -U postgres -c "CREATE DATABASE intelimed_db OWNER intelimed;"

# 2. Backend (terminal 1)
cd backend
python -m venv venv
venv\Scripts\pip install -r requirements.txt
copy .env.example .env        # fill in values
venv\Scripts\python init_db.py
venv\Scripts\uvicorn app.main:app --reload

# 3. Push script — dev mode (terminal 2)
cd sync
pip install requests python-dotenv openpyxl xlwings
copy .env.example .env        # set MINIPC_API_URL=http://localhost:8000 + SYNC_API_KEY
python excel_push.py --file ..\datos_fake.xlsx --loop   # test with static file
python excel_push.py --loop                             # live Excel via xlwings

# 4. Frontend (terminal 3)
cd frontend
npm install
npm run dev
# → http://localhost:5173  (login: admin / admin123)
```

## xlwings notes (Windows)
- Requires `pip install xlwings` and running `python path/to/pywin32_postinstall.py -install` once after fresh install
- Excel must be open before running the push script
- If Excel is in edit mode or showing a dialog, the read times out after 15s and skips the cycle (logged as WARNING)
- `EXCEL_WORKBOOK_NAME` in `.env` filters to a specific workbook by partial name match; leave blank to use the first open workbook

## What's next (not yet built)

### Core / unblocked
- **Tailscale setup** — install on Work PC and Mini PC, verify connectivity, update `MINIPC_API_URL` in sync `.env` to the Mini PC's Tailscale IP
- **Dashboard/summary view** in the frontend (waiting on contents of client's summary sheet)
- **Role-based access** (`role` column exists in users table, not enforced yet)
- **User management** (add/remove users — currently only seeded via init_db.py)

### Monitoring / observability
- **Admin monitoring page** (frontend, role-gated to `admin`):
  - Last push time + staleness warning if too old
  - Recent log lines from `excel_push.log`
  - System status: DB reachable, Excel running, last push success/fail
- **Extended `/health` endpoint**: returns last sync timestamp, row counts, error state
- **RDP on Mini PC**: essential fallback for when the URL itself is unreachable

### Deployment (Mini PC)
- PostgreSQL as a Windows service (auto-starts)
- FastAPI via Task Scheduler or NSSM as a Windows service
- `excel_push.py` via Task Scheduler on the Work PC (auto-start on login, restart on failure)
- Tailscale installed on both machines

## Pending decisions / blockers
- **Client approval** of the push architecture (currently on `feature/win32com-push` branch)
- **Sheet layout**: pushing client to use one table per sheet (currently multiple tables per sheet — incompatible with current data model)
- **Summary/dashboard sheet**: first sheet is non-tabular — plan is to rebuild as a proper web dashboard view. Waiting on contents.
- **Outside dashboard access**: do users access via Tailscale (install on each device) or via public URL + JWT only? Tailscale is cleaner security-wise but requires install on user devices.

## Key decisions made
- **xlwings push over Syncthing**: Work PC pushes live in-memory Excel data directly to the Mini PC via HTTP. No file sync needed, works from home, lower latency than any file-based approach.
- **xlwings over raw win32com**: xlwings handles COM automation edge cases better. `GetActiveObject` failed on this machine; xlwings `apps.active` worked correctly.
- **Tailscale for connectivity**: zero-config VPN, free tier sufficient, handles office and remote transparently. No port forwarding or DDNS needed.
- **API key for push endpoint**: separate from JWT auth. Compared with `secrets.compare_digest` to prevent timing attacks. Hidden from public API docs (`include_in_schema=False`).
- **Mini PC over VPS**: client prefers on-premises.
- **JSONB storage**: each row stored as JSON blob — flexible schema across sheets with different headers.
- **No ORM**: raw psycopg2 with RealDictCursor — simple enough that SQLAlchemy would be overhead.
- **bcrypt directly**: passlib dropped because it breaks with newer bcrypt versions.
- **15s read timeout**: if Excel is busy (edit mode, dialog open), the cycle is skipped rather than blocking. Logged as WARNING.
