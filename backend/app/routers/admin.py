from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from app.database import get_db
from app.auth import get_current_user

router = APIRouter()

def require_admin(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin":
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
    role: str = "viewer" #Viewer por default

@router.post("/users", status_code=201)
def create_user(body: CreateUserRequest, current_user: dict = Depends(require_admin)):
    from app.auth import hash_password
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE username = %s", (body.username,))
            if cur.fetchone():
                raise HTTPException(
                    status_code=400,
                    detail="Nombre de usuario ya existe"
                )
            cur.execute("INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s) RETURNING id, username, role, created_at",
                        (body.username, hash_password(body.password), body.role))
            new_user = cur.fetchone()
    return dict(new_user)

@router.delete("/users/{user_id}", status_code=204)
def delete_user(user_id: int, current_user: dict = Depends(require_admin)):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT username FROM users WHERE id = %s", (user_id,))
            user = cur.fetchone()
            if user and user["username"] == current_user["sub"]:
                raise HTTPException(
                    status_code=400,
                    detail="No puedes eliminar tu propio usuario"
                )
            cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
            if cur.rowcount == 0:
                raise HTTPException(
                    status_code=404,
                    detail="Usuario no encontrado"
                )

class UpdateUserSheetsRequest(BaseModel):
    sheet_ids: list[int]

@router.put("/users/{user_id}/sheets", status_code=200)
def update_user_sheets(user_id: int, body: UpdateUserSheetsRequest, current_user: dict = Depends(require_admin)):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE id = %s", (user_id,))
            if not cur.fetchone():
                raise HTTPException(
                    status_code=404,
                    detail="Usuario no encontrado"
                )
            # Eliminar asignaciones actuales
            cur.execute("DELETE FROM user_sheets WHERE user_id = %s", (user_id,))
            # Insertar nuevas asignaciones
            for sheet_id in body.sheet_ids:
                cur.execute("INSERT INTO user_sheets (user_id, sheet_id) VALUES (%s, %s)", (user_id, sheet_id))
    return {"user_id": user_id, "sheet_ids": body.sheet_ids}