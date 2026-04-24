from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from psycopg2.extras import execute_values
from app.database import get_db
from app.auth import get_current_user, hash_password
import os

router = APIRouter()


def require_admin(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requiere Acceso Administrador"
        )
    return current_user


@router.get("/users")
def list_users(current_user: dict = Depends(require_admin)):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT u.id, u.username, u.role, u.is_superuser, u.created_at,
                       COALESCE(
                           json_agg(us.sheet_id) FILTER (WHERE us.sheet_id IS NOT NULL),
                           '[]'
                       ) AS sheet_ids
                FROM users u
                LEFT JOIN user_sheets us ON u.id = us.user_id
                GROUP BY u.id
                ORDER BY u.created_at
            """)
            users = cur.fetchall()
    return [dict(u) for u in users]


class CreateUserRequest(BaseModel):
    username: str
    password: str
    role: str = "viewer"


@router.post("/users", status_code=201)
def create_user(body: CreateUserRequest, current_user: dict = Depends(require_admin)):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (username, password_hash, role)
                VALUES (%s, %s, %s)
                ON CONFLICT (username) DO NOTHING
                RETURNING id, username, role, created_at
                """,
                (body.username, hash_password(body.password), body.role)
            )
            new_user = cur.fetchone()
            if not new_user:
                raise HTTPException(status_code=400, detail="Nombre de usuario ya existe")
    return dict(new_user)


@router.delete("/users/{user_id}", status_code=204)
def delete_user(user_id: int, current_user: dict = Depends(require_admin)):
    if user_id == current_user["user_id"]:
        raise HTTPException(status_code=400, detail="No puedes eliminar tu propio usuario")
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT is_superuser FROM users WHERE id = %s", (user_id,))
            target = cur.fetchone()
            if not target:
                raise HTTPException(status_code=404, detail="Usuario no encontrado")
            if target["is_superuser"]:
                raise HTTPException(status_code=403, detail="No se puede eliminar al superusuario")
            cur.execute("DELETE FROM users WHERE id = %s", (user_id,))


class UpdateUserSheetsRequest(BaseModel):
    sheet_ids: list[int]


@router.put("/users/{user_id}/sheets", status_code=200)
def update_user_sheets(user_id: int, body: UpdateUserSheetsRequest, current_user: dict = Depends(require_admin)):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE id = %s", (user_id,))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Usuario no encontrado")
            cur.execute("DELETE FROM user_sheets WHERE user_id = %s", (user_id,))
            if body.sheet_ids:
                execute_values(
                    cur,
                    "INSERT INTO user_sheets (user_id, sheet_id) VALUES %s",
                    [(user_id, sheet_id) for sheet_id in body.sheet_ids]
                )
    return {"user_id": user_id, "sheet_ids": body.sheet_ids}


_SYNC_LOG_PATH = os.getenv(
    "SYNC_LOG_PATH",
    os.path.join(os.path.dirname(__file__), "../../../sync/excel_push.log")
)
_LOG_TAIL_LINES = 80


@router.get("/status")
def get_status(current_user: dict = Depends(require_admin)):
    # DB query — non-fatal if DB is down
    db_ok = True
    sheets = []
    db_error = None
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT s.name, s.display_name, s.last_synced_at,
                           COUNT(sd.id) AS row_count
                    FROM sheets s
                    LEFT JOIN sheet_data sd ON sd.sheet_id = s.id
                    WHERE s.is_active = true
                    GROUP BY s.id
                    ORDER BY s.name
                """)
                sheets = [dict(r) for r in cur.fetchall()]
    except Exception as e:
        db_ok = False
        db_error = str(e)

    # Log file — always readable regardless of DB state
    log_lines = []
    log_missing = False
    log_path = os.path.normpath(_SYNC_LOG_PATH)
    if os.path.exists(log_path):
        with open(log_path, "r", encoding="utf-8") as f:
            log_lines = f.readlines()[-_LOG_TAIL_LINES:]
        log_lines = [l.rstrip("\n") for l in log_lines]
    else:
        log_missing = True

    last_sync_at = None
    for s in sheets:
        t = s.get("last_synced_at")
        if t and (last_sync_at is None or t > last_sync_at):
            last_sync_at = t

    return {
        "db_ok": db_ok,
        "db_error": db_error,
        "last_sync_at": last_sync_at,
        "sheets": sheets,
        "log_lines": log_lines,
        "log_missing": log_missing,
    }