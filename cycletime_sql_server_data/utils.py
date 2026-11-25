from datetime import datetime, timezone

import pandas as pd

from psycopg2.extras import execute_values

from pony.orm import db_session

from database import (
    pg_cursor,
    pg_conn,
)

from config import (
    SCHEMA_NAME,
    TABLE_NAME,
    CYCLE_TIME_PARAMETER_MAPPING,
)

from models import (
    CycleTimeLimits,
    CorrectiveActivity,
)


# ============================================================
# Startup: verify / create tables
# ============================================================

def create_table():
    """
    Called once at startup. Checks whether the required tables
    exist and creates them if they don't.

    Order of operations
    -------------------
    1. Create schema (no-op if already present)
    2. Check cycle_time_machines
         → create if absent
         → insert default data if empty
    3. Check sql_server_mct_data
         → create if absent with FK to cycle_time_machines
         → convert to TimescaleDB hypertable (if just created or not already)
    4. Check sql_sync_state
         → create if absent
    """
    try:
        # ── 1. Schema ────────────────────────────────────────
        pg_cursor.execute(
            f"CREATE SCHEMA IF NOT EXISTS {SCHEMA_NAME};"
        )
        pg_conn.commit()
        print(f"[INIT] Schema '{SCHEMA_NAME}' OK")

        # ── 2. cycle_time_machines table ─────────────────────
        pg_cursor.execute(
            f"""
            SELECT EXISTS (
                SELECT 1
                FROM   information_schema.tables
                WHERE  table_schema = %s
                AND    table_name   = 'cycle_time_machines'
            );
            """,
            (SCHEMA_NAME,),
        )
        machines_table_exists = pg_cursor.fetchone()[0]

        if not machines_table_exists:
            print(
                f"[INIT] Table '{SCHEMA_NAME}.cycle_time_machines' not found "
                f"— creating..."
            )
            pg_cursor.execute(
                f"""
                CREATE TABLE {SCHEMA_NAME}.cycle_time_machines (
                    id             SERIAL       PRIMARY KEY,
                    machine_name   VARCHAR(100) NOT NULL,
                    line           VARCHAR(50)  NOT NULL
                );
                """
            )
            pg_conn.commit()
            print(
                f"[INIT] ✅ Table '{SCHEMA_NAME}.cycle_time_machines' created"
            )
        else:
            print(
                f"[INIT] ✅ Table '{SCHEMA_NAME}.cycle_time_machines' "
                f"already exists"
            )

        # ── Insert default data if table is empty ─────────────
        pg_cursor.execute(
            f"""
            SELECT COUNT(*)
            FROM   {SCHEMA_NAME}.cycle_time_machines;
            """
        )
        row_count = pg_cursor.fetchone()[0]

        if row_count == 0:
            print(
                f"[INIT] Table '{SCHEMA_NAME}.cycle_time_machines' is empty "
                f"— inserting default data..."
            )
            default_data = [
                (85, "OP150_A", "BLOCK"),
                (86, "OP170_A", "BLOCK"),
                (87, "OP190_A", "BLOCK"),
                (88, "OP200_A", "BLOCK"),
                (89, "OP210_A", "BLOCK"),
                (90, "OP220_A", "BLOCK"),
                (91, "OP550-1_B", "BLOCK"),
                (92, "OP550-2_B", "BLOCK"),
                (93, "OP550-4_B", "BLOCK"),
                (94, "OP550-5_B", "BLOCK"),
                (95, "OP550-6_B", "BLOCK"),
                (96, "OP550-7_B", "BLOCK"),
                (97, "OP550-8_B", "BLOCK"),
                (98, "OP550-9_B", "BLOCK"),
                (99, "OP550-10_B", "BLOCK"),
                (100, "OP550-11_B", "BLOCK"),
                (65, "OP5_A", "CRANK"),
                (66, "OP20_A", "CRANK"),
                (67, "OP50_C", "CRANK"),
                (68, "OP70_C", "CRANK"),
                (69, "OP105_C", "CRANK"),
                (70, "OP110_D", "CRANK"),
                (71, "OP120_D", "CRANK"),
                (72, "OP128_E", "CRANK"),
                (73, "OP130_E", "CRANK"),
                (74, "OP140_E", "CRANK"),
                (75, "OP150-170_F", "CRANK"),
                (76, "OP180_G", "CRANK"),
                (77, "OP200_G", "CRANK"),
                (78, "OP220_G", "CRANK"),
                (79, "OP900_A", "CRANK"),
                (80, "OP901_C", "CRANK"),
                (81, "OP902_D", "CRANK"),
                (82, "OP903_F", "CRANK"),
                (83, "OP904_G", "CRANK"),
                (84, "OP905_G", "CRANK"),
                (1, "Laser Cladding A", "Head Line"),
                (2, "T_B_OP160", "BLOCK"),
                (3, "T_B_OP180", "BLOCK"),
                (4, "T_B_OP195A", "BLOCK"),
                (5, "T_B_OP195B", "BLOCK"),
                (6, "T_B_OP230", "BLOCK"),
                (7, "T_B_OP235", "BLOCK"),
                (8, "T_B_OP540", "BLOCK"),
                (9, "T_C_OP10", "CRANK"),
                (10, "T_C_OP100", "CRANK"),
                (11, "T_C_OP160", "CRANK"),
                (12, "T_C_OP190", "CRANK"),
                (13, "T_C_OP30", "CRANK"),
                (14, "T_C_OP40", "CRANK"),
                (15, "T_C_OP90", "CRANK"),
                (16, "T_C_OP910", "CRANK"),
                (17, "T_C_OP911", "CRANK"),
                (18, "T_C_OP912", "CRANK"),
                (19, "T_C_OP913", "CRANK"),
                (20, "T_C_OP914", "CRANK"),
                (21, "T_C_OP915", "CRANK"),
                (22, "T_C_OP916", "CRANK"),
                (23, "T_H_OP10", "HEAD"),
                (24, "T_H_OP100A", "HEAD"),
                (25, "T_H_OP100B", "HEAD"),
                (26, "T_H_OP110A", "HEAD"),
                (27, "T_H_OP110B", "HEAD"),
                (28, "T_H_OP120A", "HEAD"),
                (29, "T_H_OP120B", "HEAD"),
                (30, "T_H_OP140A", "HEAD"),
                (31, "T_H_OP140B", "HEAD"),
                (32, "T_H_OP150A", "HEAD"),
                (33, "T_H_OP150B", "HEAD"),
                (34, "T_H_OP160A", "HEAD"),
                (35, "T_H_OP160B", "HEAD"),
                (36, "T_H_OP170A", "HEAD"),
                (37, "T_H_OP170B", "HEAD"),
                (38, "T_H_OP180A", "HEAD"),
                (39, "T_H_OP180B", "HEAD"),
                (40, "T_H_OP20", "HEAD"),
                (41, "T_H_OP230", "HEAD"),
                (42, "T_H_OP240", "HEAD"),
                (43, "T_H_OP250", "HEAD"),
                (44, "T_H_OP260", "HEAD"),
                (45, "T_H_OP270", "HEAD"),
                (46, "T_H_OP280", "HEAD"),
                (47, "T_H_OP285", "HEAD"),
                (48, "T_H_OP300", "HEAD"),
                (49, "T_H_OP50", "HEAD"),
                (50, "T_H_OP500", "HEAD"),
                (51, "T_H_OP510", "HEAD"),
                (52, "T_H_OP520", "HEAD"),
                (53, "T_H_OP530", "HEAD"),
                (54, "T_H_OP540", "HEAD"),
                (55, "T_H_OP55", "HEAD"),
                (56, "T_H_OP550", "HEAD"),
                (57, "T_H_OP80A", "HEAD"),
                (58, "T_H_OP80B", "HEAD"),
                (59, "T_H_OP90A", "HEAD"),
                (60, "T_H_OP90B", "HEAD"),
                (61, "JOURNAL FINISH-GRINDING_JOP_105", "CRANK"),
                (62, "JOURNAL FINISH-GRINDING_JOP_130", "CRANK"),
                (63, "JOURNAL FINISH-GRINDING_JOP_140", "CRANK"),
                (64, "Laser Cladding B", "Head Line"),
            ]
            execute_values(
                pg_cursor,
                f"""
                INSERT INTO {SCHEMA_NAME}.cycle_time_machines (id, machine_name, line)
                VALUES %s
                """,
                default_data
            )
            pg_conn.commit()
            print(
                f"[INIT] ✅ Inserted {len(default_data)} default records "
                f"into '{SCHEMA_NAME}.cycle_time_machines'"
            )
        else:
            print(
                f"[INIT] ✅ Table '{SCHEMA_NAME}.cycle_time_machines' "
                f"already has {row_count} record(s)"
            )

        # ── 3. Main data table ───────────────────────────────
        pg_cursor.execute(
            f"""
            SELECT EXISTS (
                SELECT 1
                FROM   information_schema.tables
                WHERE  table_schema = %s
                AND    table_name   = %s
            );
            """,
            (SCHEMA_NAME, TABLE_NAME.lower()),
        )
        data_table_exists = pg_cursor.fetchone()[0]

        if not data_table_exists:
            print(
                f"[INIT] Table '{SCHEMA_NAME}.{TABLE_NAME}' not found "
                f"— creating..."
            )
            pg_cursor.execute(
                f"""
                CREATE TABLE {SCHEMA_NAME}.{TABLE_NAME} (
                    time           TIMESTAMP    NOT NULL,
                    machine_id     INTEGER,
                    machine_number VARCHAR(50),
                    cycle_time     FLOAT,
                    model          INTEGER,
                    counter        INTEGER,
                    created_at     TIMESTAMPTZ  DEFAULT NOW(),

                    CONSTRAINT fk_machine
                        FOREIGN KEY (machine_id)
                        REFERENCES {SCHEMA_NAME}.cycle_time_machines(id)
                );
                """
            )
            pg_conn.commit()
            print(f"[INIT] ✅ Table '{SCHEMA_NAME}.{TABLE_NAME}' created")
        else:
            print(
                f"[INIT] ✅ Table '{SCHEMA_NAME}.{TABLE_NAME}' "
                f"already exists"
            )

        # ── Convert to TimescaleDB hypertable ────────────────
        # create_hypertable must run OUTSIDE a transaction block
        # so we commit first and set autocommit=True temporarily.
        # Check if already a hypertable first.
        pg_cursor.execute(
            f"""
            SELECT EXISTS (
                SELECT 1
                FROM   timescaledb_information.hypertables
                WHERE  hypertable_schema = %s
                AND    hypertable_name   = %s
            );
            """,
            (SCHEMA_NAME, TABLE_NAME.lower()),
        )
        is_hypertable = pg_cursor.fetchone()[0]

        if not is_hypertable:
            pg_conn.autocommit = True
            try:
                pg_cursor.execute(
                    f"""
                    SELECT create_hypertable(
                        '{SCHEMA_NAME}.{TABLE_NAME}',
                        'time'
                    );
                    """
                )
                print(
                    f"[INIT] ✅ '{SCHEMA_NAME}.{TABLE_NAME}' "
                    f"converted to hypertable"
                )
            except Exception as ht_err:
                # If TimescaleDB extension is not installed this
                # will fail gracefully — data still inserts normally.
                print(
                    f"[INIT] ⚠  Could not create hypertable "
                    f"(TimescaleDB installed?): {ht_err}"
                )
            finally:
                pg_conn.autocommit = False
        else:
            print(
                f"[INIT] ✅ '{SCHEMA_NAME}.{TABLE_NAME}' "
                f"is already a hypertable"
            )

        # ── 4. Sync-state tracking table ────────────────────
        # One row per SQL Server — stores last successfully-synced
        # timestamp so each server advances its own cursor
        # independently.
        pg_cursor.execute(
            f"""
            SELECT EXISTS (
                SELECT 1
                FROM   information_schema.tables
                WHERE  table_schema = %s
                AND    table_name   = 'sql_sync_state'
            );
            """,
            (SCHEMA_NAME,),
        )
        state_table_exists = pg_cursor.fetchone()[0]

        if not state_table_exists:
            print(
                f"[INIT] Table '{SCHEMA_NAME}.sql_sync_state' not found "
                f"— creating..."
            )
            pg_cursor.execute(
                f"""
                CREATE TABLE {SCHEMA_NAME}.sql_sync_state (
                    server_id   VARCHAR(50)  PRIMARY KEY,
                    last_synced TIMESTAMP    NOT NULL
                );
                """
            )
            pg_conn.commit()
            print(
                f"[INIT] ✅ Table '{SCHEMA_NAME}.sql_sync_state' created"
            )
        else:
            print(
                f"[INIT] ✅ Table '{SCHEMA_NAME}.sql_sync_state' "
                f"already exists"
            )

    except Exception as e:
        print(f"[INIT] ❌ Error during table initialisation: {e}")
        pg_conn.rollback()
        raise


# ============================================================
# Per-server timestamp helpers
# ============================================================

def get_last_timestamp(server_id: str):
    """
    Return the last successfully-synced timestamp for *this*
    SQL Server (identified by server_id), or None on first run.

    Querying sql_sync_state (keyed by server_id) means each
    server has its own independent cursor — a fast server's
    timestamp can never suppress a slower server's pending rows.
    """
    pg_cursor.execute(
        f"""
        SELECT last_synced
        FROM   {SCHEMA_NAME}.sql_sync_state
        WHERE  server_id = %s;
        """,
        (server_id,),
    )
    result = pg_cursor.fetchone()
    return result[0] if result else None


def update_sync_state(server_id: str, last_synced):
    """
    Upsert the last-synced timestamp for server_id.
    Called after a successful batch insert so the cursor only
    advances when data is safely committed.
    """
    pg_cursor.execute(
        f"""
        INSERT INTO {SCHEMA_NAME}.sql_sync_state (server_id, last_synced)
        VALUES (%s, %s)
        ON CONFLICT (server_id)
        DO UPDATE SET last_synced = EXCLUDED.last_synced;
        """,
        (server_id, last_synced),
    )
    # Caller (migrate_to_postgres) commits the full transaction


# ============================================================
# Fetch from SQL Server
# ============================================================

def fetch_sql_server_data(sql_conn, server_id: str) -> pd.DataFrame:
    """
    Fetch rows from Cycle_Time on the given SQL Server connection
    that are newer than the last synced timestamp for server_id.
    Returns an empty DataFrame when there is nothing new.
    """
    try:
        sql_cursor = sql_conn.cursor()

        last_timestamp = get_last_timestamp(server_id)

        if last_timestamp:
            query = """
            SELECT
                machine_number,
                CONVERT(varchar(33), timestamp_timezone, 126)
                    AS timestamp_timezone,
                cycle_time,
                model,
                counter
            FROM Cycle_Time
            WHERE timestamp_timezone > ?
            ORDER BY timestamp_timezone
            """
            sql_cursor.execute(query, last_timestamp)
            print(
                f"  [{server_id}] Incremental sync since {last_timestamp}"
            )
        else:
            query = """
            SELECT
                machine_number,
                CONVERT(varchar(33), timestamp_timezone, 126)
                    AS timestamp_timezone,
                cycle_time,
                model,
                counter
            FROM Cycle_Time
            ORDER BY timestamp_timezone
            """
            sql_cursor.execute(query)
            print(f"  [{server_id}] Initial full sync (no prior state)")

        rows    = sql_cursor.fetchall()
        columns = [col[0] for col in sql_cursor.description]
        df      = pd.DataFrame.from_records(rows, columns=columns)

        if not df.empty:
            df["timestamp_timezone"] = pd.to_datetime(
                df["timestamp_timezone"], utc=True
            ).dt.tz_convert(None)

        sql_cursor.close()

        print(f"  [{server_id}] Found {len(df)} new record(s)")
        return df

    except Exception as e:
        print(f"  [{server_id}] ❌ Error fetching data: {e}")
        raise


# ============================================================
# Insert into PostgreSQL
# ============================================================

def migrate_to_postgres(
    df: pd.DataFrame,
    machine_mapping: dict,
    server_id: str,
):
    """
    Filter df through machine_mapping, insert valid rows into
    PostgreSQL, then advance the sync cursor for server_id to
    the maximum timestamp just inserted.
    """
    try:
        data_to_insert = []
        max_ts         = None

        for _, row in df.iterrows():
            machine_number = str(row["machine_number"])
            machine_id     = machine_mapping.get(machine_number)

            if machine_id is None:
                print(
                    f"  [{server_id}] ⚠  No mapping for "
                    f"'{machine_number}' — skipped"
                )
                continue

            ts = row["timestamp_timezone"]
            data_to_insert.append(
                (
                    ts,
                    machine_id,
                    machine_number,
                    float(row["cycle_time"]),
                    int(row["model"]),
                    int(row["counter"]),
                )
            )

            if max_ts is None or ts > max_ts:
                max_ts = ts

        if not data_to_insert:
            print(
                f"  [{server_id}] No valid rows to insert "
                f"after mapping filter"
            )
            return

        insert_query = f"""
        INSERT INTO {SCHEMA_NAME}.{TABLE_NAME}
            (time, machine_id, machine_number, cycle_time, model, counter)
        VALUES %s
        """

        execute_values(pg_cursor, insert_query, data_to_insert)

        # Advance the per-server cursor ONLY after a successful insert
        update_sync_state(server_id, max_ts)

        pg_conn.commit()

        print(
            f"  [{server_id}] ✅ Inserted {len(data_to_insert)} record(s) "
            f"| cursor → {max_ts}"
        )

        # Perform cycle time anomaly detection
        detect_cycle_time_anomalies(df, machine_mapping, server_id)

    except Exception as e:
        print(f"  [{server_id}] ❌ Error inserting data: {e}")
        pg_conn.rollback()
        raise


# ============================================================
# Cycle Time Anomaly Detection
# ============================================================

def detect_cycle_time_anomalies(
    df: pd.DataFrame,
    machine_mapping: dict,
    server_id: str,
):
    """
    Detect cycle time anomalies by checking the latest 20 rows per machine
    from sql_server_mct_data. If 10+ rows exceed warning/critical limits,
    insert or update corrective_activity records.
    """
    try:
        if df.empty:
            return

        print(f"  [{server_id}] 🔍 Starting cycle time anomaly detection...")

        # Get unique machine_ids from fetched rows
        machine_ids = set()
        for _, row in df.iterrows():
            machine_number = str(row["machine_number"])
            machine_id = machine_mapping.get(machine_number)
            if machine_id is not None:
                machine_ids.add(machine_id)

        if not machine_ids:
            print(f"  [{server_id}] No valid machine data for anomaly detection")
            return

        # Fetch cycle time limits for all machines
        with db_session:
            limits = CycleTimeLimits.select(
                lambda c: c.machine_id in machine_ids
            )[:]
            limits_dict = {limit.machine_id: limit for limit in limits}

        # Check each machine for anomalies using latest 10 rows
        with db_session:
            for machine_id in machine_ids:
                # Get limits for this machine
                limit = limits_dict.get(machine_id)
                if limit is None:
                    print(
                        f"  [{server_id}] ⚠  No cycle time limits for "
                        f"machine_id {machine_id} — skipped"
                    )
                    continue

                # Fetch latest 20 rows for this machine from sql_server_mct_data
                pg_cursor.execute(
                    f"""
                    SELECT time, cycle_time
                    FROM {SCHEMA_NAME}.{TABLE_NAME}
                    WHERE machine_id = %s
                    ORDER BY time DESC
                    LIMIT 20
                    """,
                    (machine_id,),
                )
                rows = pg_cursor.fetchall()

                if len(rows) < 10:
                    # Need at least 10 rows to check
                    continue

                # Count rows exceeding limits
                warning_count = 0
                critical_count = 0
                max_cycle_time = 0
                latest_timestamp = None

                for time, cycle_time in rows:
                    if cycle_time > limit.critical_limit:
                        critical_count += 1
                    elif cycle_time > limit.warning_limit:
                        warning_count += 1

                    if cycle_time > max_cycle_time:
                        max_cycle_time = cycle_time
                    if latest_timestamp is None or time > latest_timestamp:
                        latest_timestamp = time

                # Determine condition based on count threshold (10+ rows)
                condition = 1  # OK
                if critical_count >= 10:
                    condition = 3  # Critical
                elif warning_count >= 10:
                    condition = 2  # Warning

                if condition == 1:
                    # Normal, no action needed
                    continue

                # Get parameter_id for this machine
                parameter_id = CYCLE_TIME_PARAMETER_MAPPING.get(machine_id)
                if parameter_id is None:
                    print(
                        f"  [{server_id}] ⚠  No parameter mapping for "
                        f"machine_id {machine_id} — skipped"
                    )
                    continue

                # Check if (parameter_id, condition) combination already exists
                existing = CorrectiveActivity.select(
                    lambda ca: ca.machine_parameters_id == parameter_id
                    and ca.parameter_condition_id == condition
                ).first()

                if existing is None:
                    # Insert new corrective activity
                    CorrectiveActivity(
                        machine_parameters_id=parameter_id,
                        date_of_identification=latest_timestamp,
                        latest_occurrence=latest_timestamp,
                        number_of_occurrences=1,
                        recent_value=max_cycle_time,
                        parameter_condition_id=condition,
                    )
                    print(
                        f"  [{server_id}] 🚨 New anomaly detected: "
                        f"machine_id={machine_id}, condition={condition}, "
                        f"warning_count={warning_count}, critical_count={critical_count}, "
                        f"max_cycle_time={max_cycle_time:.2f}"
                    )
                else:
                    # Update existing corrective activity
                    existing.number_of_occurrences += 1
                    existing.latest_occurrence = latest_timestamp
                    existing.recent_value = max_cycle_time
                    print(
                        f"  [{server_id}] 🔄 Updated anomaly: "
                        f"machine_id={machine_id}, condition={condition}, "
                        f"warning_count={warning_count}, critical_count={critical_count}, "
                        f"occurrences={existing.number_of_occurrences}"
                    )

        print(f"  [{server_id}] ✅ Anomaly detection completed")

    except Exception as e:
        print(f"  [{server_id}] ❌ Error in anomaly detection: {e}")
        raise
