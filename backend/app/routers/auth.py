import os
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from app.database import get_db
from app.auth import verify_password, create_access_token

router = APIRouter()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
ALLOWED_DOMAIN = os.getenv("ALLOWED_DOMAIN", "")


class LoginRequest(BaseModel):
    username: str
    password: str


class GoogleLoginRequest(BaseModel):
    token: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    role: str


@router.post("/login", response_model=TokenResponse)
def login(credentials: LoginRequest):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE username = %s", (credentials.username,))
            user = cur.fetchone()

    if not user or not user["password_hash"] or not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
        )

    token = create_access_token({"sub": user["username"], "role": user["role"], "user_id": user["id"]})
    return TokenResponse(access_token=token, username=user["username"], role=user["role"])


@router.post("/google", response_model=TokenResponse)
def google_login(body: GoogleLoginRequest):
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Google OAuth no configurado en el servidor.")

    try:
        idinfo = id_token.verify_oauth2_token(body.token, google_requests.Request(), GOOGLE_CLIENT_ID)
    except ValueError:
        raise HTTPException(status_code=401, detail="Token de Google inválido.")

    if not idinfo.get("email_verified"):
        raise HTTPException(status_code=401, detail="Email no verificado por Google.")

    email = idinfo["email"]
    domain = email.split("@")[-1]

    if ALLOWED_DOMAIN and domain != ALLOWED_DOMAIN:
        raise HTTPException(status_code=403, detail="Este email no está autorizado para acceder.")

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE email = %s", (email,))
            user = cur.fetchone()

            if not user:
                # Auto-create on first Google login with viewer role
                base = email.split("@")[0]
                username = base
                suffix = 1
                while True:
                    cur.execute("SELECT id FROM users WHERE username = %s", (username,))
                    if not cur.fetchone():
                        break
                    username = f"{base}{suffix}"
                    suffix += 1

                cur.execute(
                    "INSERT INTO users (username, email, role, is_superuser) VALUES (%s, %s, 'viewer', false) RETURNING *",
                    (username, email),
                )
                user = cur.fetchone()

    token = create_access_token({"sub": user["username"], "role": user["role"], "user_id": user["id"]})
    return TokenResponse(access_token=token, username=user["username"], role=user["role"])
