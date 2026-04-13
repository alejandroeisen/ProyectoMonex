"""Run once to initialize tables and create the default admin user."""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from app.database import init_db, get_db
from app.auth import hash_password

if __name__ == "__main__":
    print("Creating tables...")
    init_db()
    print("Tables ready.")

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE username = 'admin'")
            if not cur.fetchone():
                cur.execute(
                    "INSERT INTO users (username, password_hash, role, is_superuser) VALUES (%s, %s, %s, %s)",
                    ("admin", hash_password("admin123"), "admin", True),
                )
                print("Default superuser created  →  username: admin  /  password: admin123")
            else:
                # Mark existing admin as superuser if not already
                cur.execute(
                    "UPDATE users SET is_superuser = TRUE WHERE username = 'admin' AND is_superuser = FALSE"
                )
                print("Admin user already exists, skipping.")

    print("Done.")
