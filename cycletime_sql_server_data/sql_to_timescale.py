import time

from database import (
    pg_conn,
    get_sql_connection,
)

from config import SQL_SERVERS

from utils import (
    create_table,
    fetch_sql_server_data,
    migrate_to_postgres,
)


def sync_server(server_cfg: dict):
    """
    Run one full sync cycle for a single SQL Server.

    Opens a fresh connection, fetches new rows, inserts them
    into PostgreSQL, then closes the SQL Server connection.
    The per-server cursor (sql_sync_state) is advanced only
    after a successful commit.

    Args:
        server_cfg: one entry from config.SQL_SERVERS, containing
                    'server_id', 'connection_string', 'machine_mapping'
    """
    server_id        = server_cfg["server_id"]
    conn_string      = server_cfg["connection_string"]
    machine_mapping  = server_cfg["machine_mapping"]

    print(f"\n── [{server_id}] Starting sync ──")

    sql_conn = None
    try:
        sql_conn = get_sql_connection(conn_string)

        df = fetch_sql_server_data(sql_conn, server_id)

        if df.empty:
            print(f"  [{server_id}] No new records found")
        else:
            migrate_to_postgres(df, machine_mapping, server_id)

    except Exception as e:
        print(f"  [{server_id}] ❌ Sync error: {e}")

    finally:
        if sql_conn:
            sql_conn.close()
            print(f"  [{server_id}] Connection closed")


def main():

    try:
        print(
            "Starting continuous incremental sync "
            "from SQL Servers to PostgreSQL...\n"
            f"Configured servers: "
            f"{[s['server_id'] for s in SQL_SERVERS]}"
        )

        # Ensure destination table + sync-state table exist
        create_table()

        while True:

            print("\n══════════════════════════════════════")
            print("Checking for new records across all servers...")
            print("══════════════════════════════════════")

            for server_cfg in SQL_SERVERS:
                sync_server(server_cfg)

            print(
                "\nAll servers synced. "
                "Waiting 60 seconds for next cycle..."
            )
            time.sleep(60)

    except KeyboardInterrupt:
        print("\n\nSync stopped by user (Ctrl-C)")

    finally:
        pg_conn.close()
        print("PostgreSQL connection closed. Bye!")


if __name__ == "__main__":
    main()