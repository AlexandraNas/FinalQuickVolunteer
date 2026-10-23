"""Add only the agreed task categories and skills (safe to run more than once).

The lists live in seed_demo.py so the database and the website use one source.
seed_demo.py already runs this step; use this script when you want the lists
without the fictional members and tasks:
    python database/seeds/seed_categories.py
"""
from seed_demo import get_connection, seed_reference_data


def main():
    connection = get_connection()
    try:
        seed_reference_data(connection)
        connection.commit()
    finally:
        connection.close()


if __name__ == "__main__":
    main()
