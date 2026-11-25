from datetime import datetime, timezone

import pandas as pd

from psycopg2.extras import execute_values

from database import (
    pg_cursor,
    pg_conn
)

from config import (
    SCHEMA_NAME,
    TABLE_NAME
)

def get_latest_history_row(machine_id):

    pg_cursor.execute(
        f"""
        SELECT status, start_time, stop_time
        FROM {SCHEMA_NAME}.disconnection_history1
        WHERE machine_id = %s
        ORDER BY start_time DESC
        LIMIT 1
        """,
        (machine_id,)
    )

    return pg_cursor.fetchone()


def handle_disconnection_history(machine_id, new_status):

    latest_row = get_latest_history_row(machine_id)

    now = datetime.now(timezone.utc)

    if latest_row is None:

        if new_status == "DISCONNECTED":

            pg_cursor.execute(
                f"""
                INSERT INTO {SCHEMA_NAME}.disconnection_history1
                    (machine_id, status, start_time, stop_time)
                VALUES (%s, %s, %s, NULL)
                """,
                (machine_id, "DISCONNECTED", now)
            )

            print(
                f"  [HISTORY] Machine {machine_id}: "
                f"First DISCONNECTED event — row inserted "
                f"(start_time={now})"
            )

        return

    latest_status, latest_start, latest_stop = latest_row

    if latest_status == "DISCONNECTED" and latest_stop is None:

        if new_status == "DISCONNECTED":

            pass

        elif new_status == "NOT_DISCONNECTED":

            pg_cursor.execute(
                f"""
                UPDATE {SCHEMA_NAME}.disconnection_history1
                SET stop_time = %s
                WHERE machine_id = %s
                  AND status = 'DISCONNECTED'
                  AND stop_time IS NULL
                """,
                (now, machine_id)
            )

            print(
                f"  [HISTORY] Machine {machine_id}: "
                f"Reconnected — stop_time={now} filled"
            )

    else:

        if new_status == "DISCONNECTED":

            pg_cursor.execute(
                f"""
                INSERT INTO {SCHEMA_NAME}.disconnection_history1
                    (machine_id, status, start_time, stop_time)
                VALUES (%s, %s, %s, NULL)
                """,
                (machine_id, "DISCONNECTED", now)
            )

            print(
                f"  [HISTORY] Machine {machine_id}: "
                f"New DISCONNECTED event — row inserted "
                f"(start_time={now})"
            )

        elif new_status == "NOT_DISCONNECTED":

            pass


def create_table():

    try:

        create_schema_query = f"""
        CREATE SCHEMA IF NOT EXISTS {SCHEMA_NAME};
        """

        pg_cursor.execute(create_schema_query)

        check_table_query = f"""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_schema = '{SCHEMA_NAME}'
            AND table_name = LOWER('{TABLE_NAME}')
        );
        """

        pg_cursor.execute(check_table_query)

        table_exists = pg_cursor.fetchone()[0]

        if not table_exists:

            create_table_query = f"""
            CREATE TABLE {SCHEMA_NAME}.{TABLE_NAME} (
                time TIMESTAMP NOT NULL,
                machine_id INTEGER,
                machine_number VARCHAR(50),
                cycle_time FLOAT,
                model INTEGER,
                counter INTEGER,
                created_at TIMESTAMPTZ DEFAULT NOW(),

                CONSTRAINT fk_machine
                FOREIGN KEY (machine_id)
                REFERENCES {SCHEMA_NAME}.machines(id)
            );
            """

            pg_cursor.execute(create_table_query)

            pg_conn.commit()

            print("✅ Table created successfully!")

        else:

            print("✅ Table already exists")

    except Exception as e:

        print(f"❌ Error creating table: {e}")

        pg_conn.rollback()

        raise

def get_last_timestamp_postgres():

    query = f"""
    SELECT MAX(time)
    FROM {SCHEMA_NAME}.{TABLE_NAME}
    """

    pg_cursor.execute(query)

    result = pg_cursor.fetchone()

    if result and result[0]:

        return result[0]

    return None

