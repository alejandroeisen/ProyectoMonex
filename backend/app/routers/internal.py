"""
internal.py — Mini PC side.

Receives Excel data pushed from the Work PC script and writes it to PostgreSQL.
Secured by API key (X-API-Key header). Not exposed in public API docs.
"""

import json
import secrets
import os

from psycopg2.extras import execute_values
from datetime import datetime

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel
from dotenv import load_dotenv

from app.database import get_db

load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))

SYNC_API_KEY = os.getenv("SYNC_API_KEY", "")

router = APIRouter(include_in_schema=False)   # hidden from public API docs


# ── Request schema ────────────────────────────────────────────────────────────

class SheetPayload(BaseModel):
    name: str
    source_sheet: str | None = None
    columns: list[str]
    rows: list[dict]


class PushPayload(BaseModel):
    sheets: list[SheetPayload]
    pushed_at: str | None = None


# ── Auth ──────────────────────────────────────────────────────────────────────

def verify_api_key(x_api_key: str = Header(...)):
    if not SYNC_API_KEY:
        raise HTTPException(status_code=500, detail="SYNC_API_KEY not configured on server.")
    # Use compare_digest to prevent timing attacks
    if not secrets.compare_digest(x_api_key, SYNC_API_KEY):
        raise HTTPException(status_code=401, detail="Invalid API key.")


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.post("/internal/push")
def receive_push(payload: PushPayload, x_api_key: str = Header(...)):
    verify_api_key(x_api_key)

    total_rows = 0

    with get_db() as conn:
        with conn.cursor() as cur:
            for position, sheet in enumerate(payload.sheets):
                # Upsert sheet metadata
                cur.execute("""
                    INSERT INTO sheets (name, display_name, source_sheet, columns, last_synced_at, position)
                    VALUES (%s, %s, %s, %s::jsonb, NOW(), %s)
                    ON CONFLICT (name) DO UPDATE SET
                        source_sheet   = EXCLUDED.source_sheet,
                        columns        = EXCLUDED.columns,
                        last_synced_at = NOW(),
                        position       = EXCLUDED.position
                    RETURNING id
                """, (sheet.name, sheet.name, sheet.source_sheet, json.dumps(sheet.columns), position))
                sheet_id = cur.fetchone()["id"]

                # Replace all rows for this sheet
                cur.execute("DELETE FROM sheet_data WHERE sheet_id = %s", (sheet_id,))
                if sheet.rows:
                    execute_values(
                        cur,
                        "INSERT INTO sheet_data (sheet_id, row_data, synced_at) "
                        "VALUES %s",
                        [(sheet_id, json.dumps(row), ) for row in sheet.rows],
                        template="(%s, %s::jsonb, NOW())",
                    )
                total_rows += len(sheet.rows)

    return {
        "status": "ok",
        "sheets_synced": len(payload.sheets),
        "total_rows": total_rows,
        "synced_at": datetime.utcnow().isoformat(),
    }
