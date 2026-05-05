# Project Context

## What this is
Internal financial dashboard built as a freelance project. Replaces an Excel-based workflow so the client's team can access live market data (stocks, exchange rates, etc.) from outside the office. Not public-facing — authenticated access only.

## Working instructions for Claude
- Always propose the next step at the end of each response unless told otherwise
- Help architect and diagram when relevant
- Always consider security concerns when building or coding

## Current status
Working dev setup. Login, sheet selector, data tables with search/sort, and frontend auto-refresh (every 30s) are functional. Push script reads live Excel via xlwings and POSTs to FastAPI, which writes to PostgreSQL. Tested end-to-end on Windows. Admin panel (user management, logs, permissions) built and tested.

**Active branch**: `feature/multi-table-parser` — multi-table Excel sheet support via `##` convention.

## Hardware setup (decided)
- **Work PC**: Xenith license + Excel. Team uses this for daily work — they edit the file constantly (adding new rows for trades on different tables). Runs `excel_push.py` silently in the background.
- **No Mini PC**: backend runs on Render (cloud). No on-premises server needed.

## The data source
**Metastock Xenith** feeds live RTD data into Excel on the Work PC via a COM add-in. The team also edits this file daily — new rows are added to tables for trade entries.

`excel_push.py` runs on the Work PC, reads live in-memory Excel data (not what's saved to disk) via **xlwings**, and POSTs it directly to the Render backend. This means:
- No file sync needed (no Syncthing, no network shares, no Mini PC)
- Data reflects the current in-memory state of Excel, not the last save
- Works whether the Work PC is at the office or at home — just needs internet
- Latency is whatever `PUSH_INTERVAL_SECONDS` is set to (default 60s)

## Architecture
```
[Work PC — office or home]
Xenith + Excel (live RTD + manual edits)
excel_push.py (xlwings reads live memory)
        |
        | HTTP POST + API key
        | (internet)
        ↓
[Render — cloud hosted]
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
- **Frontend**: React (Vite), plain CSS — deployed on Render (static site)
- **Database**: PostgreSQL on Render (JSONB for row data — flexible schema, different headers per sheet)
- **Push script**: `sync/excel_push.py` — xlwings (live Excel, Windows Work PC) or `--file` mode for dev/testing
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
│   │       ├── internal.py   ← POST /internal/push (API key auth, hidden from docs)
│   │       └── admin.py      ← user management + sheet permissions (admin only)
│   ├── init_db.py            ← run once: creates tables + seeds superuser admin (admin/admin123)
│   ├── requirements.txt
│   └── .env.example
├── sync/
│   ├── excel_push.py         ← runs on Work PC (Windows). xlwings mode or --file for dev.
│   ├── excel_push.log        ← rotating log written by excel_push.py
│   └── .env.example
├── datos_fake.xlsx            ← static dev/test data (used with --file mode)
└── frontend/
    └── src/
        ├── App.jsx            ← auth state, routes between Login and Dashboard
        ├── api.js             ← all fetch calls to backend
        ├── pages/
        │   ├── Login.jsx/css
        │   ├── Dashboard.jsx/css   ← sidebar sheet selector + main content area
        │   ├── AdminPanel.jsx/css  ← user management + sheet permissions (admin only)
        │   └── LogsPanel.jsx/css   ← DB status, push log tail, sheet counts (admin only)
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
copy .env.example .env        # fill in values (SYNC_API_KEY, SECRET_KEY, etc.)
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

## Local dev setup (Linux, for backend/frontend work)
```bash
# 1. PostgreSQL
sudo -u postgres psql -c "CREATE USER intelimed WITH PASSWORD 'intelimed123';"
sudo -u postgres psql -c "CREATE DATABASE intelimed_db OWNER intelimed;"

# 2. Backend
cd backend
python3 -m venv venv
venv/bin/pip install -r requirements.txt
cp .env.example .env
venv/bin/python init_db.py
venv/bin/uvicorn app.main:app --reload

# 3. Populate DB for testing (Linux — no xlwings)
cd sync
python3 -m venv venv
venv/bin/pip install openpyxl psycopg2-binary python-dotenv
# Push fake data directly to local backend:
# python excel_push.py --file ../datos_fake.xlsx  (if xlwings mode is skipped)

# 4. Frontend
cd frontend
npm install
npm run dev
```

## xlwings notes (Windows)
- Requires `pip install xlwings` and running `python path/to/pywin32_postinstall.py -install` once after fresh install
- Excel must be open before running the push script
- If Excel is in edit mode or showing a dialog, the read times out after 15s and skips the cycle (logged as WARNING)
- `EXCEL_WORKBOOK_NAME` in `.env` filters to a specific workbook by partial name match; leave blank to use the first open workbook
- win32com was tried first but failed: `GetActiveObject` couldn't find Excel, and the file was locked when opened via path. xlwings `apps.active` solved both issues.

## What's done
- ✅ Push architecture: xlwings on Work PC → `/internal/push` → PostgreSQL
- ✅ Role-based access: admin vs viewer enforced, JWT carries user_id + role
- ✅ User management UI: Admin tab in sidebar — create/delete users, assign sheet permissions
- ✅ Superuser concept: `is_superuser` flag, default admin protected from deletion
- ✅ Logs tab: DB status, last push time with stale warning, sheet row counts, push log tail (auto-refreshes 10s)
- ✅ Stale data banner: when auto-refresh fails, table stays visible with yellow warning
- ✅ Sidebar retries sheet list every 10s if initial load failed
- ✅ Full test suite: 31 tests across auth, sheets, admin endpoints
- ✅ Render deploy config: `VITE_API_URL`, `ALLOWED_ORIGINS`, `.env.production`
- ✅ Multi-table parser: `##TableName` convention splits one Excel sheet into N named tables, each surfaced as a separate sidebar entry. Parser is in `sync/excel_push.py:parse_tables_from_rows()`.

## What's next

### Core / unblocked
- **Frontend: render multiple tables per sheet** — parser is done; frontend still renders one table per sidebar entry. Need to verify sidebar entry = table name (not sheet name) end-to-end with backend.
- **localStorage cache for last-seen sheet data** — so page loads while backend is down still show data
  - ~500KB total for real data (12 sheets, 1500 rows, 10 cols) — fits localStorage fine
  - Write only the active sheet per refresh (~38KB) — negligible
- **Dashboard/summary view** in the frontend (waiting on contents of client's summary sheet)
- **Logs tab update**: currently tails `sync.log` (old pull script). Should tail `excel_push.log` instead.

### Deployment (Render)
- Backend: deploy as Render Web Service (Python), set env vars (DATABASE_URL, SECRET_KEY, SYNC_API_KEY, ALLOWED_ORIGINS)
- Frontend: deploy as Render Static Site, set `VITE_API_URL` build env var
- Database: Render PostgreSQL managed instance
- Push script: Task Scheduler on Work PC (auto-start on login, restart on failure)

## Pending decisions / blockers
- **Summary/dashboard sheet**: first sheet is non-tabular — plan is to rebuild as a proper web dashboard view. Waiting on contents.
- **User access to dashboard**: do users reach it via the Render URL directly (public URL + JWT)? Yes — that's the plan.

## Multi-table sheet convention (`##`)

Client's Excel sheets contain multiple tables stacked vertically. Rather than forcing a restructure, a lightweight convention was agreed:

- Pushing client to prefixes each table's title cell with `##` (e.g. `##Posiciones`, `##Monedas-PUT`)
- The parser in `parse_tables_from_rows()` treats any row with exactly one non-None cell starting with `##` as a new table boundary
- The next non-empty row after the title becomes the column headers
- All subsequent rows until the next `##` row are data — blank rows within a table are ignored
- If no `##` markers exist on a sheet, the whole sheet is parsed as one table (backward compatible)
- Each parsed table is emitted as its own named entry in the push payload, so the frontend sidebar shows them as independent sheets

**Edge cases handled:**
- Blank rows mid-table: ignored (not a split boundary)
- Whitespace around `##`: stripped (`"  ##  Monedas-PUT  "` → `"Monedas-PUT"`)
- Single-value data rows (e.g. `Subtotal`): treated as data, not a title (no `##` prefix)
- `##` title with no header row: logged as WARNING and skipped
- Two `##` tables with no blank rows between them: works correctly
- Table with headers but zero data rows: emitted with 0 rows (valid)

**Test file:** `datos_fake.xlsx` covers all of the above edge cases. Run with:
```bash
sync/venv/bin/python sync/excel_push.py --file datos_fake.xlsx
```

## Key decisions made
- **Render over Mini PC**: no on-premises server. Client no longer needs to buy/maintain hardware. Work PC pushes to cloud.
- **xlwings push over Syncthing**: Work PC pushes live in-memory Excel data directly to Render via HTTP. No file sync needed, works from home, lower latency than any file-based approach.
- **xlwings over raw win32com**: xlwings handles COM automation edge cases better. `GetActiveObject` failed; xlwings `apps.active` worked correctly.
- **API key for push endpoint**: separate from JWT auth. Compared with `secrets.compare_digest` to prevent timing attacks. Hidden from public API docs (`include_in_schema=False`).
- **JSONB storage**: each row stored as JSON blob — flexible schema across sheets with different headers.
- **No ORM**: raw psycopg2 with RealDictCursor — simple enough that SQLAlchemy would be overhead.
- **bcrypt directly**: passlib dropped because it breaks with newer bcrypt versions.
- **15s read timeout**: if Excel is busy (edit mode, dialog open), the cycle is skipped rather than blocking. Logged as WARNING.
