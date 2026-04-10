from fastapi import APIRouter, Depends, HTTPException
from app.database import get_db
from app.auth import get_current_user

router = APIRouter()


@router.get("/")
def list_sheets(current_user: dict = Depends(get_current_user)):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, name, display_name, columns, last_synced_at
                FROM sheets
                WHERE is_active = true
                ORDER BY name
            """)
            sheets = cur.fetchall()
    return [dict(s) for s in sheets]


@router.get("/{sheet_id}/data")
def get_sheet_data(sheet_id: int, current_user: dict = Depends(get_current_user)):
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM sheets WHERE id = %s AND is_active = true",
                (sheet_id,)
            )
            sheet = cur.fetchone()
            if not sheet:
                raise HTTPException(status_code=404, detail="Sheet not found")

            cur.execute(
                "SELECT row_data FROM sheet_data WHERE sheet_id = %s ORDER BY id",
                (sheet_id,)
            )
            rows = cur.fetchall()

    return {
        "sheet": dict(sheet),
        "rows": [r["row_data"] for r in rows],
    }
