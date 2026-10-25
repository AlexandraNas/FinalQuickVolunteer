import os

import mysql.connector
from mysql.connector import Error, pooling

# A small pool of open connections is reused between requests. Opening a new
# encrypted connection to the online database for every request was the
# slowest part of loading a page. close() on a pooled connection hands it back
# to the pool instead of closing it, so the routes do not change.
POOL_SIZE = int(os.environ.get("MYSQL_POOL_SIZE", "5"))
_pools = {}


def _settings(database_name):
    return {
        "host": os.environ.get("MYSQL_HOST", "127.0.0.1"),
        "port": int(os.environ.get("MYSQL_PORT", "3306")),
        "user": os.environ.get("MYSQL_USER", "quickvolunteer_app"),
        "password": os.environ["MYSQL_PASSWORD"],
        "database": database_name,
    }


def _pool_for(settings):
    key = (settings["host"], settings["port"], settings["user"], settings["database"])
    pool = _pools.get(key)
    if pool is None:
        pool = pooling.MySQLConnectionPool(
            pool_name="qv_" + str(len(_pools)),
            pool_size=POOL_SIZE,
            pool_reset_session=True,
            **settings
        )
        _pools[key] = pool
    return pool


def get_db_connection():
    database_name = os.environ.get(
        "MYSQL_DATABASE",
        "quickvolunteer_db"
    )

    # Automated tests must explicitly use the test database.
    if os.environ.get("QUICKVOLUNTEER_TESTING") == "1":
        if database_name != "quickvolunteer_test_db":
            raise RuntimeError(
                "Tests must use quickvolunteer_test_db"
            )

    settings = _settings(database_name)

    try:
        try:
            connection = _pool_for(settings).get_connection()
        except pooling.PoolError:
            # Every pooled connection is busy: open a normal one for this request.
            return mysql.connector.connect(**settings)

        # The database closes connections that sit unused for a long time
        # (for example while the free Render server sleeps): reconnect if so.
        connection.ping(reconnect=True, attempts=2, delay=0)
        return connection

    except Error as error:
        print(f"MySQL connection error: {error}")
        raise
