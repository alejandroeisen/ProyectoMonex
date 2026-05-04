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

## 1. Render PostgreSQL

Create → **New PostgreSQL** on Render. Once provisioned:

- Copy the **Internal Database URL** — used for `DATABASE_URL` in the backend service (step 2)
- Copy the **External Database URL** — keep it aside for running `change_password.py` locally later

---

## 2. Render Backend (Web Service)

Create → **New Web Service** → connect the repo.

| Setting | Value |
|---|---|
| Root directory | `backend` |
| Build command | `pip install -r requirements.txt` |
| Start command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |

Environment variables to set:

| Variable | Value |
|---|---|
| `DATABASE_URL` | Internal Database URL from step 1 |
| `SECRET_KEY` | Generated in step 0 |
| `SYNC_API_KEY` | Generated in step 0 |
| `GOOGLE_CLIENT_ID` | `447376070623-teri6gj21dkj3h55makkmv4f9jf9pcg1.apps.googleusercontent.com` |
| `ALLOWED_DOMAIN` | `monex.cl` |
| `ALLOWED_ORIGINS` | Frontend Render URL (fill in after step 3, e.g. `https://proyectomonex.onrender.com`) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `480` |

Deploy. Once live, confirm it's up: `GET https://[backend-url]/health` should return `{"status":"ok"}`.

The tables and default `admin` user are created automatically on first startup (`init_db` runs at startup).

---

## 3. Render Frontend (Static Site)

Create → **New Static Site** → connect the repo.

| Setting | Value |
|---|---|
| Root directory | `frontend` |
| Build command | `npm install && npm run build` |
| Publish directory | `dist` |

Build environment variables:

| Variable | Value |
|---|---|
| `VITE_API_URL` | Backend Render URL from step 2 |
| `VITE_GOOGLE_CLIENT_ID` | `447376070623-teri6gj21dkj3h55makkmv4f9jf9pcg1.apps.googleusercontent.com` |

Deploy. Note the frontend URL — go back to step 2 and fill in `ALLOWED_ORIGINS` if you haven't already (triggers a redeploy of the backend).

---

## 4. Google Cloud Console

[console.cloud.google.com](https://console.cloud.google.com) → the dashboard project → **APIs & Services** → **Credentials** → the OAuth 2.0 client → **Authorized JavaScript origins** → add the frontend Render URL:

```
https://[frontend-url].onrender.com
```

Without this, Google will reject the OAuth login with an `origin_mismatch` error.

---

## 5. Post-deploy checks

1. Open the frontend URL — the login screen should appear
2. Log in with `admin` / `admin123` using the password login (click "Acceso de administrador")
3. Confirm the Admin and Logs tabs load without errors
4. **Change the admin password immediately** using `change_password.py`:
   - Temporarily replace `DATABASE_URL` in `backend/.env` with the External Database URL from step 1
   - Run: `venv/bin/python change_password.py`
   - Restore `backend/.env` to the local value after

---

## 6. Work PC setup

1. Copy the `sync/` folder to the Work PC (any path, e.g. `C:\Monex\sync\`)
2. Copy `sync/.env.example` → `sync/.env` and fill in:
   - `MINIPC_API_URL` = backend Render URL
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

## 7. Handoff

- Share the frontend URL with the client
- Walk through `docs/USER_ACCESS.md` with whoever will be the admin
- Delete any test user accounts created with `@intelimed.ai` from the Admin panel
