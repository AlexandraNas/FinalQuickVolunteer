"""First start on Render: create the tables and demo data if the database is empty.

Render runs this before the app starts (see the start command in DEPLOY_RENDER.md),
so nobody needs to connect to the database from their own computer.

- The tables and tasks already exist -> it does nothing, so data is never overwritten.
- The tables exist but are empty -> it adds the demo data.
- The database is empty -> it creates the 15 tables, adds the demo data and,
  if DEMO_PASSWORD is set (12+ characters), the demo logins.
- Any problem is printed in the Render log and the app still starts.

To start again with fresh demo data (this DELETES everything in the database,
including accounts and tasks people created), set RESET_DATABASE to
"yes-delete-everything" in Render, deploy once, then remove the setting.
"""
import os
import subprocess
import sys
from pathlib import Path

import mysql.connector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from load_schema import SCHEMA, statements  # noqa: E402


def connect():
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", "127.0.0.1"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER", "quickvolunteer_app"),
        password=os.environ["MYSQL_PASSWORD"],
        database=os.getenv("MYSQL_DATABASE", "quickvolunteer_db"),
        connection_timeout=20,
    )


def main():
    connection = connect()
    cursor = connection.cursor()
    try:
        if os.getenv("RESET_DATABASE") == "yes-delete-everything":
            cursor.execute("SHOW TABLES")
            tables = [row[0] for row in cursor.fetchall()]
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
            for table in tables:
                cursor.execute(f"DROP TABLE `{table}`")
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
            connection.commit()
            print(f"Setup: RESET_DATABASE is on, {len(tables)} tables deleted. "
                  "Remove RESET_DATABASE in Render now.")

        cursor.execute("SHOW TABLES LIKE 'users'")
        if cursor.fetchone():
            cursor.execute("SELECT COUNT(*) FROM tasks")
            if cursor.fetchone()[0] > 0:
                print("Setup: tables and data already exist, nothing to do.", flush=True)
                return
            print("Setup: tables exist but have no tasks yet, adding the demo data.", flush=True)
        else:
            for statement in statements(SCHEMA.read_text(encoding="utf-8")):
                cursor.execute(statement)
            connection.commit()
            print("Setup: 15 tables created.", flush=True)
    finally:
        cursor.close()
        connection.close()

    seeds = HERE / "seeds"
    subprocess.run([sys.executable, str(seeds / "seed_demo.py")], check=True)
    if len(os.getenv("DEMO_PASSWORD", "")) >= 12:
        subprocess.run([sys.executable, str(seeds / "demo_logins.py")], check=True)
    else:
        print("Setup: DEMO_PASSWORD not set (12+ characters), demo logins skipped.")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:  # the website should still start
        print(f"Setup problem: {error}")
