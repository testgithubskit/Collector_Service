import pyodbc
import psycopg2

from config import (
    DATABASE_URL,
    POSTGRES_HOST,
    POSTGRES_PORT,
    POSTGRES_DATABASE,
    POSTGRES_USER,
    POSTGRES_PASSWORD,
)

from pony.orm import *
from models import db


# ============================================================
# PostgreSQL / TimescaleDB — single shared connection
# ============================================================
pg_conn   = psycopg2.connect(DATABASE_URL)
pg_cursor = pg_conn.cursor()

print(
    f"[DB] ✅ PostgreSQL connected successfully "
    f"→ {POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DATABASE}"
)


# ============================================================
# Pony ORM binding (for model-based access if needed)
# ============================================================
db.bind(
    provider="postgres",
    user=POSTGRES_USER,
    password=POSTGRES_PASSWORD,
    host=POSTGRES_HOST,
    database=POSTGRES_DATABASE,
    port=POSTGRES_PORT,
)

db.generate_mapping(create_tables=True)


# ============================================================
# SQL Server — open a fresh connection on demand
# ============================================================
def get_sql_connection(connection_string: str):
    """
    Open and return a new pyodbc connection using the supplied
    ODBC connection string.  The caller is responsible for
    closing the connection when done.

    Opens fresh per sync-cycle so stale connections (e.g. after
    a long sleep or a network hiccup) are avoided automatically.
    """
    try:
        conn = pyodbc.connect(connection_string, timeout=10)
        return conn
    except pyodbc.Error as e:
        print(f"[DB] ❌ Failed to connect to SQL Server: {e}")
        raise
