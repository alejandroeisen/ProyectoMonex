import psycopg2
import psycopg2.extras
from contextlib import contextmanager
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))

DATABASE_URL = os.getenv("DATABASE_URL")


@contextmanager
def get_db():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(255) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    role VARCHAR(50) DEFAULT 'viewer',
                    created_at TIMESTAMP DEFAULT NOW()
                );

                CREATE TABLE IF NOT EXISTS sheets (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) UNIQUE NOT NULL,
                    display_name VARCHAR(255),
                    columns JSONB,
                    last_synced_at TIMESTAMP,
                    is_active BOOLEAN DEFAULT true
                );

                CREATE TABLE IF NOT EXISTS sheet_data (
                    id SERIAL PRIMARY KEY,
                    sheet_id INTEGER REFERENCES sheets(id) ON DELETE CASCADE,
                    row_data JSONB NOT NULL,
                    synced_at TIMESTAMP DEFAULT NOW()
                );
                        
                CREATE TABLE IF NOT EXISTS user_sheets (
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    sheet_id INTEGER REFERENCES sheets(id) ON DELETE CASCADE,
                    PRIMARY KEY (user_id, sheet_id)
                );
            """)
            # Safe migration: adds column to existing DBs without breaking new ones
            cur.execute("""
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS is_superuser BOOLEAN DEFAULT FALSE;
            """)
