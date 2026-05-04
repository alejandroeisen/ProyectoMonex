from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, sheets, internal, admin
from app.database import init_db, get_db
from app.auth import hash_password

app = FastAPI(title="Monex Dashboard")

import os

ALLOWED_ORIGINS = [
    "http://localhost:5173",
    *[o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()],
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()
    _seed_admin()


def _seed_admin():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE username = 'admin'")
            if not cur.fetchone():
                cur.execute(
                    "INSERT INTO users (username, password_hash, role, is_superuser) VALUES (%s, %s, %s, %s)",
                    ("admin", hash_password("admin123"), "admin", True),
                )


app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(sheets.router, prefix="/sheets", tags=["sheets"])
app.include_router(internal.router)   # no prefix — endpoint is /internal/push
app.include_router(admin.router, prefix="/admin", tags=["admin"])


@app.get("/health")
def health():
    return {"status": "ok"}
