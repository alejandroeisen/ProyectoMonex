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

This must be done under the client's Google account (or a Google Cloud project they own), so the OAuth consent screen is tied to their organization.

1. Go to [console.cloud.google.com](https://console.cloud.google.com) and create a new project
2. Enable the **Google+ API** (or **Google Identity**)
3. Go to **APIs & Services** → **Credentials** → **Create Credentials** → **OAuth 2.0 Client ID**
   - Application type: **Web application**
   - Authorized JavaScript origins: add the frontend Render URL once you have it (step 3) — you can come back and add it after
4. Copy the generated **Client ID** — you'll need it in steps 2 and 3

---

## 2. Render PostgreSQL

Create → **New PostgreSQL** on Render. Once provisioned:

- Copy the **Internal Database URL** — used for `DATABASE_URL` in the backend service (step 3)
- Copy the **External Database URL** — keep it aside for running `change_password.py` locally later

---

## 3. Render Backend (Web Service)

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
| `ALLOWED_ORIGINS` | Frontend Render URL (fill in after step 4, e.g. `https://proyectomonex.onrender.com`) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `480` |
| `ADMIN_INITIAL_PASSWORD` | A strong password of your choice |

Deploy. Once live, confirm it's up: `GET https://[backend-url]/health` should return `{"status":"ok"}`.

Tables and the `admin` user are created automatically on first startup, using `ADMIN_INITIAL_PASSWORD` as the password. After that the env var has no effect and can be removed from Render.

---

## 4. Render Frontend (Static Site)

Before deploying, update `frontend/.env.production` in the repo with the real values:

```
VITE_API_URL=https://[backend-url].onrender.com
VITE_GOOGLE_CLIENT_ID=[client ID from step 1]
```

Then create → **New Static Site** → connect the repo.

| Setting | Value |
|---|---|
| Root directory | `frontend` |
| Build command | `npm install && npm run build` |
| Publish directory | `dist` |

Build environment variables (these override `.env.production` on Render):

| Variable | Value |
|---|---|
| `VITE_API_URL` | Backend Render URL from step 3 |
| `VITE_GOOGLE_CLIENT_ID` | Client ID from step 1 |

Deploy. Note the frontend URL — go back to step 3 and fill in `ALLOWED_ORIGINS`, which will trigger a backend redeploy.

---

## 5. Google Cloud — add authorized origin

Back in Google Cloud Console → the OAuth client from step 1 → **Authorized JavaScript origins** → add:

```
https://[frontend-url].onrender.com
```

Without this, Google rejects the OAuth login with an `origin_mismatch` error.

---

## 6. Post-deploy checks

1. Open the frontend URL — the login screen should appear
2. Log in with `admin` / the value you set for `ADMIN_INITIAL_PASSWORD` using the password login (click "Acceso de administrador")
3. Confirm the Admin and Logs tabs load without errors

To change the admin password at any point, use the Render Shell on the backend service:
```
python change_password.py
```

---

## 7. Work PC setup

1. Copy the `sync/` folder to the Work PC (any path, e.g. `C:\Monex\sync\`)
2. Copy `sync/.env.example` → `sync/.env` and fill in:
   - `MINIPC_API_URL` = backend Render URL from step 3
   - `SYNC_API_KEY` = the key generated in step 0
   - `EXCEL_WORKBOOK_NAME` = partial name of the client's workbook
3. Open a terminal in `sync/` and run:
   ```
   pip install requests python-dotenv openpyxl xlwings
   ```
4. Right-click `registrar_tarea.bat` → **Run as administrator**
5. Confirm the task appears in Windows Task Scheduler as `Monex Excel Push`
6. Open Excel with the workbook, then run: `schtasks /run /tn "Monex Excel Push"`
7. Check `sync\excel_push.log` — should show successful pushes within 15 seconds

---

## 8. Handoff

- Share the frontend URL with the client
- Walk through `docs/USER_ACCESS.md` with whoever will be the admin
- Delete any test user accounts created with `@intelimed.ai` from the Admin panel
