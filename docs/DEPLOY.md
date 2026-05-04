# Deployment Checklist

Steps to go from this repo to a live production system on Render.

---

## 0. Before you start

Generate two secrets and keep them handy — you'll paste them into Render:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"  # run twice
```

First output → `SECRET_KEY`  
Second output → `SYNC_API_KEY` (also goes in the Work PC `.env`)

---

## 1. Google Cloud — create OAuth client

This must be done under the client's Google account so the OAuth consent screen is tied to their organization.

1. Go to [console.cloud.google.com](https://console.cloud.google.com) and create a new project

2. Go to **APIs & Services** → **OAuth consent screen**:
   - If the client has **Google Workspace**: set User Type to **Internal** — this automatically restricts login to their org domain, no further configuration needed
   - If not: set to **External**, fill in app name and contact email, add `monex.cl` under **Authorized domains**
   - Complete the form and save

3. Go to **APIs & Services** → **Credentials** → **Create Credentials** → **OAuth 2.0 Client ID**:
   - Application type: **Web application**
   - Authorized JavaScript origins: leave blank for now — you'll add the frontend URL in step 5
   - Click **Create**

4. Copy the generated **Client ID** — you'll need it in steps 3 and 4

---

## 2. Render PostgreSQL

Create → **New PostgreSQL** on Render. Wait for it to finish provisioning (takes ~1 minute), then copy the **Internal Database URL** from the **Info** tab — you'll need it in step 3.

---

## 3. Render Backend (Web Service)

> If this is a fresh Render account, you'll need to authorize GitHub access when connecting the repo — Render will prompt you to do this automatically.

Create → **New Web Service** → connect the repo.

| Setting | Value |
|---|---|
| Root directory | `backend` |
| Build command | `pip install -r requirements.txt` |
| Start command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |

Environment variables to set:

| Variable | Value |
|---|---|
| `DATABASE_URL` | Internal Database URL from step 2 |
| `SECRET_KEY` | Generated in step 0 |
| `SYNC_API_KEY` | Generated in step 0 |
| `GOOGLE_CLIENT_ID` | Client ID from step 1 |
| `ALLOWED_DOMAIN` | `monex.cl` |
| `ALLOWED_ORIGINS` | Leave blank for now — fill in after step 4 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `480` |
| `ADMIN_INITIAL_PASSWORD` | A strong password of your choice |

Deploy. Once live, open `https://[service-name].onrender.com/health` in a browser — it should show `{"status":"ok"}`.

Tables and the `admin` user are created automatically on first startup, using `ADMIN_INITIAL_PASSWORD` as the password. After that the env var has no effect and can be removed.

> **Render free tier note:** free tier web services sleep after 15 minutes of inactivity. The push script will log connection failures while the backend is asleep and recover once it wakes up (~30s). For a production deployment use at least the Starter paid plan to avoid this.

---

## 4. Render Frontend (Static Site)

Create → **New Static Site** → connect the repo (same repo, Render will ask which branch to use).

| Setting | Value |
|---|---|
| Root directory | `frontend` |
| Build command | `npm install && npm run build` |
| Publish directory | `dist` |

Build environment variables (Vite bakes these in at build time):

| Variable | Value |
|---|---|
| `VITE_API_URL` | Backend Render URL from step 3 (e.g. `https://[service-name].onrender.com`) |
| `VITE_GOOGLE_CLIENT_ID` | Client ID from step 1 |

Deploy. Once you have the frontend URL, go to Render → backend service → **Environment** tab → set `ALLOWED_ORIGINS` to the frontend URL → **Save Changes** (this triggers a backend redeploy automatically).

---

## 5. Google Cloud — add authorized origin

Back in Google Cloud Console → **APIs & Services** → **Credentials** → the OAuth client from step 1 → **Authorized JavaScript origins** → add:

```
https://[frontend-url].onrender.com
```

Click **Save**. Without this, Google rejects the OAuth login with an `origin_mismatch` error.

---

## 6. Post-deploy checks

1. Open the frontend URL — the login screen should appear
2. Log in with `admin` / the value you set for `ADMIN_INITIAL_PASSWORD` (click "Acceso de administrador")
3. Confirm the Admin and Logs tabs load without errors

To change the admin password at any point, go to Render → backend service → **Shell** tab and run:
```
python change_password.py
```

---

## 7. Work PC setup

1. Get the `sync/` folder onto the Work PC — easiest is to download the repo as a ZIP from GitHub (**Code** → **Download ZIP**), unzip it anywhere, and use the `sync/` folder inside. Or clone the full repo if git is installed.

2. Copy `sync/.env.example` → `sync/.env` and fill in:
   - `MINIPC_API_URL` = backend Render URL from step 3
   - `SYNC_API_KEY` = the key generated in step 0
   - `EXCEL_WORKBOOK_NAME` = partial name of the client's workbook (e.g. `Monex` matches `Monex_2024.xlsx`)

3. Open a terminal (`cmd`) in the `sync/` folder and install dependencies:
   ```
   pip install requests python-dotenv openpyxl xlwings
   ```

4. Run the xlwings post-install step (required once on Windows):
   - Find the xlwings install path:
     ```
     python -c "import xlwings; print(xlwings.__file__)"
     ```
     This prints something like `C:\Users\Name\...\site-packages\xlwings\__init__.py`
   - Take that path, remove `xlwings\__init__.py` from the end, and add `pywin32_postinstall.py`:
     ```
     python C:\Users\Name\...\site-packages\pywin32_postinstall.py -install
     ```
   - "Shortcut creation skipped" in the output is fine — no errors is what matters.

5. Open Excel with the client's workbook before continuing.

6. Right-click `registrar_tarea.bat` → **Run as administrator**

7. Confirm the task appears in Windows Task Scheduler as `Monex Excel Push`

8. Start it immediately without rebooting:
   ```
   schtasks /run /tn "Monex Excel Push"
   ```

9. Check `sync\excel_push.log` — should show successful pushes within 15 seconds

> **Note:** Excel must be open with the workbook loaded whenever the push script runs. If Excel is closed the script logs a warning and skips that cycle — no data is lost, it just pauses until Excel is available again.

---

## 8. Handoff

- Share the frontend URL with the client
- Walk through `docs/USER_ACCESS.md` with whoever will be the admin
- Delete any test user accounts created with `@intelimed.ai` from the Admin panel
