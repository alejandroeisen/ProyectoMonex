"""
Run once to change the password of any password-based user (e.g. the admin superuser).

Usage:
    python change_password.py
    python change_password.py --username admin
"""
import sys
import os
import argparse
import getpass

sys.path.insert(0, os.path.dirname(__file__))

from app.database import get_db, init_db
from app.auth import hash_password


def main():
    parser = argparse.ArgumentParser(description="Change a user's password")
    parser.add_argument("--username", default="admin", help="Username to update (default: admin)")
    args = parser.parse_args()

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, username, is_superuser FROM users WHERE username = %s", (args.username,))
            user = cur.fetchone()

    if not user:
        print(f"Error: user '{args.username}' not found.")
        sys.exit(1)

    print(f"Changing password for user: {user['username']}")

    while True:
        new_password = getpass.getpass("New password: ")
        if len(new_password) < 8:
            print("Password must be at least 8 characters. Try again.")
            continue
        confirm = getpass.getpass("Confirm password: ")
        if new_password != confirm:
            print("Passwords do not match. Try again.")
            continue
        break

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET password_hash = %s WHERE username = %s",
                (hash_password(new_password), args.username),
            )

    print(f"Password updated successfully for '{args.username}'.")


if __name__ == "__main__":
    main()
