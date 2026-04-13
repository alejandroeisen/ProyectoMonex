from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from psycopg2.extras import execute_values
from app.database import get_db
from app.auth import get_current_user, hash_password

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
                SELECT u.id, u.username, u.role, u.created_at,
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
            cur.execute("DELETE FROM users WHERE id = %s RETURNING id", (user_id,))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Usuario no encontrado")


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