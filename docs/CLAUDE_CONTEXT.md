# Project Briefing for Claude

Paste this at the start of a new Claude conversation to give it full context before troubleshooting.

---

## What this is

Internal financial dashboard for a client (Monex). Replaces an Excel-based workflow. Authenticated users access live market data from a web dashboard. Not public-facing.

## Architecture

```
[Work PC — Windows]
Excel open with live RTD data (Metastock Xenith)
excel_push.py runs in background via Task Scheduler
reads live Excel data via xlwings → POSTs to Render every 15s
        |
        | HTTP POST + SYNC_API_KEY header
        ↓
[Render — cloud]
FastAPI backend (Python) → PostgreSQL
        |
React frontend (static site on Render)
        ↑
[Users — anywhere, JWT authenticated via Google OAuth]
```

## Tech stack

- **Backend**: Python, FastAPI, psycopg2, python-jose (JWT), bcrypt, google-auth
- **Frontend**: React (Vite), plain CSS — static site on Render
- **Database**: PostgreSQL on Render (JSONB for row data)
- **Push script**: `sync/excel_push.py` — xlwings reads live Excel on Windows Work PC
- **Auth**: Google OAuth (domain-restricted to monex.cl) + emergency admin account with password
- **Sync API key**: shared secret between push script and backend, header `X-API-Key`

## Key files on the Work PC

```
sync/
├── excel_push.py         ← the push script (runs via Task Scheduler)
├── excel_push.log        ← rotating log, check this first when diagnosing
├── .env                  ← config: MINIPC_API_URL, SYNC_API_KEY, EXCEL_WORKBOOK_NAME
├── start_push.bat        ← launcher (called by Task Scheduler)
└── registrar_tarea.bat   ← one-time setup: registers the Task Scheduler task
```

## Environment variables (sync/.env on Work PC)

| Variable | Purpose |
|---|---|
| `MINIPC_API_URL` | Render backend URL, e.g. `https://xxx.onrender.com` |
| `SYNC_API_KEY` | Shared secret — must match the backend's `SYNC_API_KEY` env var |
| `EXCEL_WORKBOOK_NAME` | Partial name match for the Excel workbook (leave blank for first open) |
| `PUSH_INTERVAL_SECONDS` | How often to push, default 15 |
| `EXCLUDED_SHEETS` | Comma-separated sheet names to skip |

## Environment variables (Render backend)

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Render PostgreSQL internal URL |
| `SECRET_KEY` | JWT signing secret |
| `SYNC_API_KEY` | Must match sync/.env on Work PC |
| `GOOGLE_CLIENT_ID` | OAuth client ID from Google Cloud Console |
| `ALLOWED_DOMAIN` | `monex.cl` — only emails from this domain can log in via Google |
| `ALLOWED_ORIGINS` | Frontend Render URL (CORS) |
| `ADMIN_INITIAL_PASSWORD` | Used only on first startup to seed the admin user |

## Common failure modes

**Push script not sending data:**
- Check `sync\excel_push.log` — look for ERROR or WARNING lines
- Excel must be open with the workbook loaded (xlwings reads live in-memory data)
- If Excel is in edit mode or showing a dialog, the read times out and the cycle is skipped (WARNING in log)
- Confirm Task Scheduler task `Monex Excel Push` is running: `schtasks /query /tn "Monex Excel Push" /fo LIST`
- Test backend reachability: GET `https://[backend-url]/health` should return `{"status":"ok"}`

**Frontend shows no data / stale data:**
- Check the Logs tab in the dashboard (admin only) — shows last push time and row counts
- If last push time is old, the issue is on the Work PC side (see above)
- If backend is on Render free tier, it may have gone to sleep — first request wakes it up (~30s)

**Login not working:**
- Google OAuth errors: check that the frontend URL is in Authorized JavaScript origins in Google Cloud Console
- `origin_mismatch`: frontend URL not whitelisted in Google Cloud Console
- User domain not allowed: `ALLOWED_DOMAIN` on the backend must match the user's email domain
- Emergency admin login: click "Acceso de administrador" on the login screen, username `admin`

**Push script runs but backend rejects pushes (401/403):**
- `SYNC_API_KEY` mismatch between `sync/.env` and Render backend env vars

## Useful diagnostic commands (run in sync/ folder on Work PC)

```bash
# Check Task Scheduler task status
schtasks /query /tn "Monex Excel Push" /fo LIST

# Run push script manually (shows live output, Ctrl+C to stop)
venv\Scripts\python excel_push.py --loop

# Run one push cycle only
venv\Scripts\python excel_push.py

# Test backend health
python -c "import requests; r = requests.get('https://[backend-url].onrender.com/health'); print(r.status_code, r.json())"

# Check last 50 lines of log
powershell -Command "Get-Content excel_push.log -Tail 50"
```

## Render dashboard access

[dashboard.render.com](https://dashboard.render.com) — backend service has a **Shell** tab for running commands directly on the server (e.g. `python change_password.py` to reset admin password, or querying the DB).
