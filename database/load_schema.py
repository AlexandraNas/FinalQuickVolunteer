"""Create the QuickVolunteer tables in an empty MySQL database (for example on Aiven).

Uses the same settings as the app: MYSQL_HOST, MYSQL_PORT, MYSQL_USER,
MYSQL_PASSWORD and MYSQL_DATABASE. Run it once, from the project folder:

    python database/load_schema.py

It stops if the tables already exist, so it never overwrites data.
"""
import os
import re
from pathlib import Path

import mysql.connector

SCHEMA = Path(__file__).resolve().parent / "schema.sql"


def statements(sql):
    sql = re.sub(r"--[^\n]*", "", sql)  # remove comments
    return [part.strip() for part in sql.split(";") if part.strip()]


def main():
    if not os.getenv("MYSQL_PASSWORD"):
        raise SystemExit("Set MYSQL_PASSWORD first.")

    connection = mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", "127.0.0.1"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER", "quickvolunteer_app"),
        password=os.environ["MYSQL_PASSWORD"],
        database=os.getenv("MYSQL_DATABASE", "quickvolunteer_db"),
    )
    cursor = connection.cursor()
    try:
        cursor.execute("SHOW TABLES LIKE 'users'")
        if cursor.fetchone():
            raise SystemExit("The tables already exist. Nothing was changed.")

        for statement in statements(SCHEMA.read_text(encoding="utf-8")):
            cursor.execute(statement)
        connection.commit()

        cursor.execute("SHOW TABLES")
        print(f"Done: {len(cursor.fetchall())} tables created.")
    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    main()
