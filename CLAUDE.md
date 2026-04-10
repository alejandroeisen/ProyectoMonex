# Project Context for Claude Code

## What this is
Internal financial dashboard for Intelimed. Replaces an Excel-based workflow so the team can access live market data (stocks, exchange rates, etc.) from outside the office. Not public-facing — authenticated access only.

## Current status
Working dev mockup. Login, sheet selector, and data tables are functional. Sync script reads a local Excel file and writes to PostgreSQL. Frontend auto-refresh (polling) has not been implemented yet.

## The data source problem
The real data comes from **Metastock Xenith** — a financial data platform that feeds live data into Excel via an RTD (Real-Time Data) COM add-in. It is NOT a REST API. The Excel file lives on a physical office PC. The plan is:
- Keep Excel running on the office PC as normal (team continues using it)
- Run the Python sync script on the same PC, reading from the live Excel instance via COM (win32com)
- For now the sync script uses openpyxl on a static file — COM integration comes later once API/Excel access is confirmed

## Architecture
```
[Metastock Xenith RTD] → [Excel on office PC]
                                |
                        [sync/excel_sync.py]  ← reads Excel, runs on schedule
                                |
                        [PostgreSQL database]
                                |
                        [FastAPI backend]  ← JWT auth, serves data
                                |
                        [React frontend]  ← login → sheet selector → table
```

Data is stored as JSONB in PostgreSQL (flexible schema — each Excel sheet has different headers, so no fixed columns).

## Tech stack
- **Backend**: Python, FastAPI, psycopg2, python-jose (JWT), bcrypt
- **Frontend**: React (Vite), plain CSS
- **Database**: PostgreSQL (JSONB for row data)
- **Sync script**: Python, openpyxl (→ win32com later for live Excel)
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
│   ├── init_db.py            ← run once: creates tables + seeds admin user
│   ├── requirements.txt
│   └── .env.example          ← copy to .env and fill in credentials
├── sync/
│   └── excel_sync.py         ← reads Excel → PostgreSQL. Pass --loop for continuous sync
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

# 3. Sync script
cd sync
python3 -m venv venv
venv/bin/pip install openpyxl psycopg2-binary python-dotenv
venv/bin/python excel_sync.py ../fake_data.xlsx         # run once
venv/bin/python excel_sync.py ../fake_data.xlsx --loop  # run continuously

# 4. Frontend
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

## What's next (not yet built)
- Frontend auto-refresh (polling every 30-60s so data updates without page reload)
- COM-based Excel reading via win32com (replaces openpyxl, reads live Xenith data)
- Windows Task Scheduler setup for the sync script (auto-start on PC boot)
- VPS deployment (likely DigitalOcean or Hetzner, ~$6/mo)
- Role-based access (column `role` already exists in users table, just not enforced yet)
- Proper user management (add/remove users — currently only seeded via init_db.py)

## Key decisions made
- **JSONB storage**: each row stored as a JSON blob because sheets have different headers. Column list stored separately in `sheets.columns`.
- **No ORM**: raw psycopg2 with RealDictCursor — simple enough that SQLAlchemy would be overhead.
- **bcrypt directly**: passlib was dropped because it breaks with newer bcrypt versions.
- **VPS over mini PC**: recurring ~$6/mo preferred over $600 upfront, though mini PC remains a valid option if the team prefers on-premises.
- **Keep Excel**: the team continues using Excel + Xenith normally. The sync script is a passive reader, not a replacement.
