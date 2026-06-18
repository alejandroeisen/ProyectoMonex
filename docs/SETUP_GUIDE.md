# Monex Dashboard — First-Time Setup Guide

## Instructions for Claude

You are helping set up the Monex Dashboard from scratch. This is an internal financial dashboard that replaces an Excel-based workflow. Here is what you are deploying:

- **Supabase** — PostgreSQL database (cloud)
- **Render** — hosts the Python/FastAPI backend and the React frontend (cloud)
- **Google Cloud** — OAuth login for users (they log in with their corporate Google account)
- **Work PC** — a Windows PC at the client's office that runs a background script reading live data from Excel and pushing it to the backend every 5 seconds

Walk the user through each step in order. Wait for confirmation at each step before moving to the next. If something fails, ask what error they see and diagnose before suggesting a fix. Do not skip steps or assume something worked unless the user confirms it.

Things to keep in mind:
- The backend auto-creates tables and the admin user on first startup — no manual DB initialization needed
- `SYNC_API_KEY` must be the same value in both Render (backend env var) and the Work PC `.env` file — if they differ, pushes will fail with 401
- The frontend bakes `VITE_API_URL` into the build at compile time — if it's wrong, the site must be redeployed, not just reconfigured
- The Work PC is Windows. All commands there are for `cmd`, not bash
- Excel must be open on the Work PC before the push script runs. If Excel is closed, the script skips that cycle and logs a warning — no data is lost
- The Supabase free tier pauses after 1 week of inactivity. Regular pushes from the Work PC reset the timer. If it ever pauses, restore it from the Supabase dashboard

---

## Step 0 — Generate secrets (do this first, keep them handy)

Run the following twice on any machine that has Python. Each run gives you one secret:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

- First output → `SECRET_KEY` (signs JWT tokens)
- Second output → `SYNC_API_KEY` (authenticates the push script — goes in both Render and Work PC)

Save both values somewhere safe before continuing.

---

## Step 1 — Supabase (database)

1. Go to [supabase.com](https://supabase.com) → **Start your project** → create an account
2. **New project** → name it (e.g. `monex`), set a strong password, pick region **South America (São Paulo)**
3. Wait ~2 minutes for provisioning

**Get the connection string:**
- Left sidebar → **Project Settings** → **Database**
- Scroll to **Connection string** → select the **Session pooler** tab
- Copy the URL. It looks like:
  `postgresql://postgres.XXXXXXXX:PASSWORD@aws-1-sa-east-1.pooler.supabase.com:5432/postgres`
- If the password contains special characters, percent-encode them (e.g. `@` → `%40`, `#` → `%23`)

Save this URL — you need it in Step 2.

---

## Step 2 — Google Cloud (OAuth)

This gives users the ability to log in with their corporate Google account.

1. Go to [console.cloud.google.com](https://console.cloud.google.com) → create a new project (name it e.g. `Monex Dashboard`)

2. Left menu → **APIs & Services** → **OAuth consent screen**:
   - If the client has **Google Workspace**: User Type → **Internal** (restricts login to their org automatically — no further domain configuration needed)
   - If not: User Type → **External**, fill in app name and contact email, add the client's domain under **Authorized domains**
   - Save and continue through all screens

3. Left menu → **APIs & Services** → **Credentials** → **Create Credentials** → **OAuth 2.0 Client ID**:
   - Application type: **Web application**
   - Name: anything (e.g. `Monex Web`)
   - **Authorized JavaScript origins**: leave blank for now — you'll add the frontend URL in Step 4
   - Click **Create**

4. Copy the **Client ID** that appears — save it, you need it in Steps 3 and 4.

---

## Step 3 — Render backend (Web Service)

1. Go to [render.com](https://render.com) → create an account → connect your GitHub account when prompted
2. Dashboard → **New** → **Web Service** → select the `ProyectoMonex` GitHub repo
3. Fill in settings:

| Setting | Value |
|---|---|
| Name | `monex-webservice` (or any name) |
| Root directory | `backend` |
| Runtime | Python 3 |
| Build command | `pip install -r requirements.txt` |
| Start command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Instance type | Free (or Starter for production — see note below) |

4. Under **Environment Variables**, add each of these:

| Variable | Value |
|---|---|
| `DATABASE_URL` | Supabase Session Pooler URL from Step 1 |
| `SECRET_KEY` | First secret from Step 0 |
| `SYNC_API_KEY` | Second secret from Step 0 |
| `GOOGLE_CLIENT_ID` | Client ID from Step 2 |
| `ALLOWED_DOMAIN` | The client's email domain (e.g. `monex.cl`) |
| `ALLOWED_ORIGINS` | Leave blank for now — you'll fill this in after Step 4 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `480` |
| `ADMIN_INITIAL_PASSWORD` | A strong password of your choice — this becomes the `admin` account password |

5. Click **Create Web Service** → wait for the deploy to finish (~3 minutes)

6. Once deployed, open `https://[your-service-name].onrender.com/health` in a browser — it should return `{"status":"ok"}`. This also confirms the DB connection worked and tables were created.

7. Note the backend URL — you need it in Step 4.

> **Free tier note:** Render free tier web services sleep after 15 minutes of inactivity. The push script will log connection failures while the backend wakes up (~30s) and recover automatically. For production use, upgrade to at least the **Starter** paid plan ($7/month) to avoid this.

---

## Step 4 — Render frontend (Static Site)

1. Dashboard → **New** → **Static Site** → select the same GitHub repo
2. Fill in settings:

| Setting | Value |
|---|---|
| Name | `monex-frontend` (or any name) |
| Root directory | `frontend` |
| Build command | `npm install && npm run build` |
| Publish directory | `dist` |

3. Under **Environment Variables** (build-time — Vite bakes these into the bundle):

| Variable | Value |
|---|---|
| `VITE_API_URL` | Backend URL from Step 3 (e.g. `https://monex-webservice.onrender.com`) |
| `VITE_GOOGLE_CLIENT_ID` | Client ID from Step 2 |

4. Click **Create Static Site** → wait for the build to finish (~2 minutes)
5. Note the frontend URL (e.g. `https://monex-frontend.onrender.com`)

---

## Step 5 — Wire CORS and Google OAuth

**Render — update CORS:**
- Go to the **backend** Web Service → **Environment** tab
- Set `ALLOWED_ORIGINS` to the frontend URL from Step 4
- Click **Save Changes** → Render redeploys the backend automatically

**Google Cloud — add authorized origin:**
- Go to [console.cloud.google.com](https://console.cloud.google.com) → the project from Step 2
- **APIs & Services** → **Credentials** → the OAuth client you created
- Under **Authorized JavaScript origins** → add the frontend URL from Step 4
- Click **Save**

Without this last step, Google rejects logins with an `origin_mismatch` error.

---

## Step 6 — Verify the deployment

1. Open the frontend URL in a browser — the login screen should appear
2. Click **"Acceso de administrador"** (bottom of the login screen) and log in with:
   - Username: `admin`
   - Password: the value you set for `ADMIN_INITIAL_PASSWORD` in Step 3
3. Confirm the **Admin** and **Logs** tabs load without errors
4. The dashboard will show no data yet — that comes from the Work PC in Step 7

**Change the admin password before handing over:**
- Go to Render → backend service → **Shell** tab
- Run: `python change_password.py`
- Follow the prompts (minimum 8 characters)

---

## Step 7 — Work PC setup (Windows, on-site)

**Before you go:**
- Prepare a `.env` file with these values already filled in:
  ```
  MINIPC_API_URL=https://[your-backend].onrender.com
  SYNC_API_KEY=[second secret from Step 0 — must match Render exactly]
  EXCEL_WORKBOOK_NAME=[partial name of the client's Excel file, e.g. "Informe"]
  EXCEL_WORKBOOK_PATH=C:\Users\[user]\Documents\[Informe.xlsx]
  PUSH_INTERVAL_SECONDS=5
  FORMAT_REFRESH_SECONDS=3600
  EXCLUDED_SHEETS=
  ```
- Ask the client the Excel filename and full path before you arrive so you can fill both `EXCEL_WORKBOOK_NAME` and `EXCEL_WORKBOOK_PATH` in advance
- `EXCEL_WORKBOOK_PATH` is the full path to the file on disk — used to read cell formatting (colors, bold) without any COM calls, so Excel doesn't freeze. Leave blank to disable formatting.

**On the client's PC:**

### 7.1 — Install Python

- Download Python 3.11 or 3.12 from [python.org](https://python.org)
- During install: **check "Add Python to PATH"** before clicking Install
- Verify: open Command Prompt (`Win+R` → type `cmd` → Enter) and run:
  ```
  python --version
  ```
  Should print `Python 3.11.x` or similar.

### 7.2 — Copy the sync folder

- Copy the `sync\` folder from the project to `C:\Monex\`
- Also copy the pre-filled `.env` file into `C:\Monex\sync\`
- Final structure should be:
  ```
  C:\Monex\sync\
    excel_push.py
    excel_push_task.xml
    registrar_tarea.bat
    start_push.bat
    .env
  ```

### 7.3 — Create virtual environment and install dependencies

Open Command Prompt and run:
```cmd
cd C:\Monex\sync
python -m venv venv
venv\Scripts\pip install requests python-dotenv xlwings openpyxl
```

### 7.4 — Run xlwings post-install (required once for COM automation)

Still in the same Command Prompt:
```cmd
venv\Scripts\python -c "import xlwings; print(xlwings.__file__)"
```

This prints a path like `C:\Monex\sync\venv\Lib\site-packages\xlwings\__init__.py`.

Take that path, remove `xlwings\__init__.py` from the end, and run:
```cmd
venv\Scripts\python C:\Monex\sync\venv\Lib\site-packages\pywin32_postinstall.py -install
```

"Shortcut creation skipped" in the output is normal — what matters is no errors.

### 7.5 — Test manually

Make sure Excel is open with the client's workbook, then:
```cmd
venv\Scripts\python C:\Monex\sync\excel_push.py
```

Wait ~10 seconds. Check `C:\Monex\sync\excel_push.log` — the last lines should show a successful push (no ERROR lines). Then open the frontend → Logs tab and confirm data appeared.

### 7.6 — Register the Task Scheduler task

Right-click `C:\Monex\sync\registrar_tarea.bat` → **Run as administrator**

The script automatically replaces the path placeholder and registers the task. You should see:
```
Tarea registrada correctamente.
```

If it says "Error al registrar la tarea", confirm you right-clicked and chose "Run as administrator".

### 7.7 — Verify the task is running

Start it immediately without rebooting:
```cmd
schtasks /run /tn "Monex Excel Push"
```

Then check `excel_push.log` again — should show new push lines within 10 seconds.

You can also open **Task Scheduler** (search in Start menu), find `Monex Excel Push`, and confirm its status is **Running**.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `/health` returns error / site won't load | Check Render logs — usually a bad `DATABASE_URL`. Confirm Supabase is not paused. |
| Login fails with `origin_mismatch` | The frontend URL was not added to Google Cloud OAuth authorized origins (Step 5) |
| Login fails with CORS error | `ALLOWED_ORIGINS` in Render doesn't match the frontend URL exactly |
| Dashboard shows data but Google login doesn't work | `VITE_GOOGLE_CLIENT_ID` is wrong — rebuild the frontend with the correct value |
| Push script exits immediately | Check `excel_push.log` — usually `SYNC_API_KEY` mismatch (401) or backend URL wrong |
| Excel freezes / lags during push | Check that `EXCEL_WORKBOOK_PATH` is set — this enables disk-based formatting reads (no COM calls). If already set, the lag is from the value read which is unavoidable but brief. |
| Formatting (colors/bold) missing in dashboard | `EXCEL_WORKBOOK_PATH` is blank or incorrect — set it to the full path of the Excel file |
| xlwings can't find Excel | Excel must be open and the workbook must be loaded before the script runs |
| xlwings COM error on startup | Re-run the pywin32 post-install step (Step 7.4) |
| Task Scheduler task doesn't appear | `registrar_tarea.bat` was not run as administrator |
| No data after setup | Check `excel_push.log` for errors, then check the Logs tab in the frontend |
| Supabase connection refused | DB is paused — go to Supabase dashboard → project → "Restore project" |

---

## Post-setup handoff

- Share the frontend URL with the client's team
- Walk the admin through the **Admin** panel — adding users, assigning table permissions
- Users log in with their corporate Google account (`@[client-domain]`) — no passwords to manage
- New users get `viewer` role automatically with no table access — an admin must grant permissions after first login
- The push script runs silently in the background on the Work PC and restarts automatically if it crashes
