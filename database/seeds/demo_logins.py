"""Give a few fictional demo accounts a known password, and create one
administrator, so the team can log in during the demo.

seed_demo.py gives every demo user a random password nobody knows, so
without this script nobody can log in as a demo user.

Run after seed_demo.py:
    export DEMO_PASSWORD="choose-at-least-12-characters"
    python database/seeds/demo_logins.py

Never use this on a real (production) database.
"""
import os

import mysql.connector
from werkzeug.security import generate_password_hash

# Fictional demo accounts from seed_demo.py that can log in.
DEMO_LOGINS = [
    "emma.wilson.demo@example.com",      # help seeker
    "james.carter.demo@example.com",     # volunteer
    "sofia.martinez.demo@example.com",   # both
]

ADMIN = ("Demo", "Admin", "admin.demo@example.com")


def main():
    if os.getenv("QUICKVOLUNTEER_TESTING") == "1":
        raise RuntimeError("Do not run demo logins in test mode.")

    password = os.environ.get("DEMO_PASSWORD", "")
    if len(password) < 12:
        raise RuntimeError("Set DEMO_PASSWORD (at least 12 characters).")

    connection = mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", "127.0.0.1"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER", "quickvolunteer_app"),
        password=os.environ["MYSQL_PASSWORD"],
        database=os.getenv("MYSQL_DATABASE", "quickvolunteer_db"),
    )
    cursor = connection.cursor()
    password_hash = generate_password_hash(password)

    try:
        for email in DEMO_LOGINS:
            cursor.execute(
                "UPDATE users SET password_hash = %s WHERE email = %s",
                (password_hash, email),
            )
            print(("Ready: " if cursor.rowcount else "Not found: ") + email)

        first, last, email = ADMIN
        cursor.execute("SELECT user_id FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            cursor.execute(
                "UPDATE users SET password_hash = %s WHERE email = %s",
                (password_hash, email),
            )
        else:
            cursor.execute(
                """
                INSERT INTO users (first_name, last_name, email,
                                   password_hash, account_type, account_status,
                                   created_at)
                VALUES (%s, %s, %s, %s, 'admin', 'active',
                        %s - INTERVAL 60 DAY)
                """,
                (first, last, email, password_hash,
                 os.getenv("DEMO_NOW", "2027-03-15 10:00:00")),
            )
        print("Ready: " + email + " (administrator)")
        connection.commit()
    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    main()
