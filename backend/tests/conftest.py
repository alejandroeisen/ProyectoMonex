"""
Test fixtures and configuration.

Uses a dedicated test database (intelimed_test_db) to avoid touching dev data.
Run once before first test run:
    sudo -u postgres psql -c "CREATE DATABASE intelimed_test_db OWNER intelimed;"

Then run tests with:
    cd backend
    venv/bin/pytest tests/ -v
"""
import os
import pytest
import psycopg2
import psycopg2.extras
from contextlib import contextmanager
from fastapi.testclient import TestClient

# Point to test DB before importing anything that reads DATABASE_URL
os.environ["DATABASE_URL"] = "postgresql://intelimed:intelimed123@localhost:5432/intelimed_test_db"

from app.main import app
from app.database import init_db
from app.auth import hash_password


# ── DB helpers ────────────────────────────────────────────────────────────────

@contextmanager
def get_test_db():
    conn = psycopg2.connect(
        os.environ["DATABASE_URL"],
        cursor_factory=psycopg2.extras.RealDictCursor
    )
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ── Session-scoped setup ──────────────────────────────────────────────────────

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Create tables once for the entire test session."""
    init_db()
    yield
    # Tear down all data after session
    with get_test_db() as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE users, sheets, sheet_data, user_sheets RESTART IDENTITY CASCADE")


# ── Per-test cleanup ──────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clean_tables():
    """Wipe all data before each test for isolation."""
    with get_test_db() as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE users, sheets, sheet_data, user_sheets RESTART IDENTITY CASCADE")
    yield


# ── Reusable fixtures ─────────────────────────────────────────────────────────

@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def admin_user():
    with get_test_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s) RETURNING id, username, role",
                ("admin", hash_password("admin123"), "admin")
            )
            return dict(cur.fetchone())


@pytest.fixture
def viewer_user():
    with get_test_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s) RETURNING id, username, role",
                ("viewer", hash_password("viewer123"), "viewer")
            )
            return dict(cur.fetchone())


@pytest.fixture
def test_sheets():
    """Insert two fake sheets with data."""
    with get_test_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO sheets (name, display_name, columns) VALUES (%s, %s, %s::jsonb) RETURNING id",
                ("Sheet1", "Sheet1", '["Ticker", "Precio"]')
            )
            sheet1_id = cur.fetchone()["id"]
            cur.execute(
                "INSERT INTO sheets (name, display_name, columns) VALUES (%s, %s, %s::jsonb) RETURNING id",
                ("Sheet2", "Sheet2", '["Fecha", "Valor"]')
            )
            sheet2_id = cur.fetchone()["id"]

            cur.execute(
                "INSERT INTO sheet_data (sheet_id, row_data) VALUES (%s, %s::jsonb)",
                (sheet1_id, '{"Ticker": "AAPL", "Precio": 182.5}')
            )
            cur.execute(
                "INSERT INTO sheet_data (sheet_id, row_data) VALUES (%s, %s::jsonb)",
                (sheet2_id, '{"Fecha": "2026-04-01", "Valor": 950}')
            )
    return {"sheet1_id": sheet1_id, "sheet2_id": sheet2_id}


@pytest.fixture
def admin_token(client, admin_user):
    res = client.post("/auth/login", json={"username": "admin", "password": "admin123"})
    return res.json()["access_token"]


@pytest.fixture
def viewer_token(client, viewer_user):
    res = client.post("/auth/login", json={"username": "viewer", "password": "viewer123"})
    return res.json()["access_token"]


def auth(token):
    """Shorthand for Authorization header dict."""
    return {"Authorization": f"Bearer {token}"}
