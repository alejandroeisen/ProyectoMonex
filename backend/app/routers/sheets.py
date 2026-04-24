from fastapi import APIRouter, Depends, HTTPException
from app.database import get_db
from app.auth import get_current_user

router = APIRouter()


@router.get("/")
def list_sheets(current_user: dict = Depends(get_current_user)):
    with get_db() as conn:
        with conn.cursor() as cur:
            if current_user["role"] == "admin":
                cur.execute("""
                    SELECT id, name, display_name, columns, last_synced_at
                    FROM sheets
                    WHERE is_active = true
                    ORDER BY name
                """)
            else:
                cur.execute("""
                    SELECT s.id, s.name, s.display_name, s.columns, s.last_synced_at
                    FROM sheets s
                    INNER JOIN user_sheets us ON s.id = us.sheet_id
                    WHERE s.is_active = true
                    AND us.user_id = %s
                    ORDER BY s.name
                """, (current_user["user_id"],))
            sheets = cur.fetchall()
    return [dict(s) for s in sheets]


@router.get("/{sheet_id}/data")
def get_sheet_data(sheet_id: int, current_user: dict = Depends(get_current_user)):
    with get_db() as conn:
        with conn.cursor() as cur:
            if current_user["role"] != "admin":
                cur.execute(
                    "SELECT 1 FROM user_sheets WHERE sheet_id = %s AND user_id = %s",
                    (sheet_id, current_user["user_id"])
                )
                if not cur.fetchone():
                    raise HTTPException(status_code=403, detail="Acceso denegado")

            cur.execute(
                "SELECT * FROM sheets WHERE id = %s AND is_active = true",
                (sheet_id,)
            )
            sheet = cur.fetchone()
            if not sheet:
                raise HTTPException(status_code=404, detail="Tabla no encontrada")

            cur.execute(
                "SELECT row_data FROM sheet_data WHERE sheet_id = %s ORDER BY id",
                (sheet_id,)
            )
            rows = cur.fetchall()

    return {
        "sheet": dict(sheet),
        "rows": [r["row_data"] for r in rows],
    }