from influxdb import InfluxDBClient
from typing import List, Optional, Dict
from datetime import datetime, timedelta, timezone
import psycopg2
from psycopg2 import sql
import os
import requests
import urllib.parse
from config import InfluxDBConfig, PostgreSQLConfig
from models import VibrationDataPoint, MachineConfig, VibrationMachineLog


class InfluxDBManager:
    """Manager for InfluxDB connections and operations"""

    def __init__(self, config: InfluxDBConfig):
        self.config = config
        self.client: Optional[InfluxDBClient] = None

    def connect(self) -> InfluxDBClient:
        """Create and return an InfluxDB client"""
        print(f"Connecting to InfluxDB at {self.config.host}:{self.config.port}...")

        self.client = InfluxDBClient(
            host=self.config.host,
            port=self.config.port,
            username=self.config.username,
            password=self.config.password,
            database=self.config.database,
            ssl=self.config.ssl,
            verify_ssl=self.config.verify_ssl,
            timeout=30
        )

        # Test connection
        self.client.ping()
        print(f"✓ Connected to InfluxDB: {self.config.host}:{self.config.port}")

        return self.client

    def fetch_port_data(self, port: str, start_time_string: str, duration_seconds: int = 60) -> List[dict]:
        """Fetch data for a specific port within a specified time window (default 60 seconds) using raw HTTP API with chunking"""
        start_time = self._parse_start_time(start_time_string)
        end_time = start_time
        start_time = start_time - timedelta(seconds=duration_seconds)

        print(f"  Checking InfluxDB for port: {port}")
        print(f"  Time range: {start_time} to {end_time} ({duration_seconds} seconds)")

        # Use raw HTTP API with 2-second chunks to avoid limits
        chunk_duration = 2  # seconds
        all_points = []

        chunk_start = start_time
        chunk_count = 0

        protocol = "https" if self.config.ssl else "http"
        url = f"{protocol}://{self.config.host}:{self.config.port}/query"
        auth = (self.config.username, self.config.password)
        verify_ssl = self.config.verify_ssl

        while chunk_start < end_time:
            chunk_end = min(chunk_start + timedelta(seconds=chunk_duration), end_time)

            query = f'SELECT * FROM "{port}" WHERE time >= \'{chunk_start.strftime("%Y-%m-%dT%H:%M:%SZ")}\' AND time < \'{chunk_end.strftime("%Y-%m-%dT%H:%M:%SZ")}\' ORDER BY time ASC'

            params = {
                "db": self.config.database,
                "q": query
            }

            chunk_count += 1
            try:
                response = requests.get(url, params=params, auth=auth, verify=verify_ssl)
                response.raise_for_status()
                data = response.json()

                # Parse the response - process ALL series returned by InfluxDB
                if "results" in data and data["results"]:
                    result = data["results"][0]
                    series_list = result.get("series", [])

                    if chunk_count <= 3:
                        print(f"  Chunk {chunk_count}: {len(series_list)} series returned")

                    for series in series_list:
                        if chunk_count <= 3:
                            print(f"    Tags: {series.get('tags', {})}, Points: {len(series.get('values', []))}")

                        columns = series["columns"]
                        for value in series.get("values", []):
                            all_points.append(dict(zip(columns, value)))

                if chunk_count % 10 == 0 or chunk_start + timedelta(seconds=chunk_duration) >= end_time:
                    print(f"  Processed {chunk_count} chunks, {len(all_points)} points so far...")

            except Exception as e:
                print(f"  ✗ Error fetching chunk {chunk_count}: {e}")

            chunk_start = chunk_end

        print(f"  Total: {len(all_points)} points found across {chunk_count} chunks")
        return all_points

    def _parse_start_time(self, start_time_string: str) -> datetime:
        """Convert ISO format string to UTC datetime"""
        dt = datetime.fromisoformat(start_time_string)
        dt = dt.replace(tzinfo=timezone.utc)
        return dt

    def close(self):
        """Close the InfluxDB connection"""
        if self.client:
            self.client.close()
            print("InfluxDB connection closed.")


class PostgreSQLManager:
    """Manager for PostgreSQL connections and operations"""

    def __init__(self, config: PostgreSQLConfig):
        self.config = config
        self.connection: Optional[psycopg2.extensions.connection] = None

    def connect(self):
        """Create and return a PostgreSQL connection"""
        print("Connecting to PostgreSQL...")

        self.connection = psycopg2.connect(
            host=self.config.host,
            port=self.config.port,
            database=self.config.database,
            user=self.config.username,
            password=self.config.password
        )
        print(f"✓ Connected to PostgreSQL: {self.config.host}:{self.config.port}/{self.config.database}")

        # Create schema if it doesn't exist
        with self.connection.cursor() as cursor:
            cursor.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier(self.config.schema)))
            self.connection.commit()

        # Set search path
        with self.connection.cursor() as cursor:
            cursor.execute(sql.SQL("SET search_path TO {}, public").format(sql.Identifier(self.config.schema)))
            self.connection.commit()

        print(f"✓ Schema set: {self.config.schema}")
        return self.connection

    def ensure_connection(self):
        """Check if connection is alive, reconnect if needed"""
        if self.connection is None or self.connection.closed:
            print("PostgreSQL connection closed, reconnecting...")
            self.connect()
        return self.connection

    def create_vibration_machines_table(self):
        """Create the vibration_machines table if it doesn't exist"""
        query = sql.SQL("""
            CREATE TABLE IF NOT EXISTS {}.vibration_machines (
                id SERIAL PRIMARY KEY,
                machine_name VARCHAR(100) NOT NULL UNIQUE,
                location VARCHAR(100),
                port1 VARCHAR(50),
                port2 VARCHAR(50),
                warning DOUBLE PRECISION,
                critical DOUBLE PRECISION
            )
        """).format(sql.Identifier(self.config.schema))

        with self.connection.cursor() as cursor:
            cursor.execute(query)

        self.connection.commit()

    def initialize_machines(self, machine_configs: Dict[str, MachineConfig]):
        """Insert machine configurations into vibration_machines table"""
        for machine_name, config in machine_configs.items():
            # Check if machine already exists
            check_query = sql.SQL("""
                SELECT COUNT(*) FROM {}.vibration_machines WHERE machine_name = %s
            """).format(sql.Identifier(self.config.schema))

            with self.connection.cursor() as cursor:
                cursor.execute(check_query, (machine_name,))
                count = cursor.fetchone()[0]

                if count == 0:
                    insert_query = sql.SQL("""
                        INSERT INTO {}.vibration_machines (id, machine_name, location, port1, port2, warning, critical)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """).format(sql.Identifier(self.config.schema))

                    cursor.execute(insert_query, (
                        config.machine_id,
                        config.machine_name,
                        config.machine_location,
                        config.port1,
                        config.port2,
                        20.0,  # warning value
                        40.0   # critical value
                    ))

        self.connection.commit()

    def create_vibration_machine_logs_table(self):
        """Create the vibration_machine_logs table if it doesn't exist"""
        query = sql.SQL("""
            CREATE TABLE IF NOT EXISTS {}.vibration_machine_logs (
                id SERIAL PRIMARY KEY,
                machine_id INTEGER REFERENCES {}.vibration_machines(id),
                program_file_id INTEGER,
                program_file_time TIMESTAMPTZ,
                baseline BOOLEAN DEFAULT FALSE,
                port VARCHAR(50),
                contact_temperature DOUBLE PRECISION,
                v_peak_x DOUBLE PRECISION,
                v_peak_y DOUBLE PRECISION,
                v_peak_z DOUBLE PRECISION,
                v_rms_x DOUBLE PRECISION,
                v_rms_y DOUBLE PRECISION,
                v_rms_z DOUBLE PRECISION,
                cycle_time DOUBLE PRECISION
            )
        """).format(sql.Identifier(self.config.schema), sql.Identifier(self.config.schema))

        with self.connection.cursor() as cursor:
            cursor.execute(query)

        self.connection.commit()

    def insert_vibration_machine_log(
        self,
        machine_id: int,
        program_file_time: datetime,
        port: Optional[str] = None,
        contact_temperature: Optional[float] = None,
        v_peak_x: Optional[float] = None,
        v_peak_y: Optional[float] = None,
        v_peak_z: Optional[float] = None,
        v_rms_x: Optional[float] = None,
        v_rms_y: Optional[float] = None,
        v_rms_z: Optional[float] = None,
        cycle_time: Optional[float] = None
    ) -> int:
        """Insert a log entry into vibration_machine_logs and return the program_file_id"""
        self.ensure_connection()
        insert_query = sql.SQL("""
            INSERT INTO {}.vibration_machine_logs (
                machine_id,
                program_file_time,
                port,
                contact_temperature,
                v_peak_x,
                v_peak_y,
                v_peak_z,
                v_rms_x,
                v_rms_y,
                v_rms_z,
                cycle_time
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """).format(sql.Identifier(self.config.schema))

        with self.connection.cursor() as cursor:
            cursor.execute(insert_query, (
                machine_id,
                program_file_time,
                port,
                contact_temperature,
                v_peak_x,
                v_peak_y,
                v_peak_z,
                v_rms_x,
                v_rms_y,
                v_rms_z,
                cycle_time
            ))
            program_file_id = cursor.fetchone()[0]

        self.connection.commit()
        return program_file_id

    def get_latest_program_file_time(self, machine_id: Optional[int] = None) -> Optional[datetime]:
        """Get the latest program_file_time from vibration_machine_logs"""
        self.ensure_connection()
        if machine_id:
            query = sql.SQL("""
                SELECT MAX(program_file_time) FROM {}.vibration_machine_logs WHERE machine_id = %s
            """).format(sql.Identifier(self.config.schema))
            with self.connection.cursor() as cursor:
                cursor.execute(query, (machine_id,))
                result = cursor.fetchone()
                return result[0] if result and result[0] else None
        else:
            query = sql.SQL("""
                SELECT MAX(program_file_time) FROM {}.vibration_machine_logs
            """).format(sql.Identifier(self.config.schema))
            with self.connection.cursor() as cursor:
                cursor.execute(query)
                result = cursor.fetchone()
                return result[0] if result and result[0] else None

    def create_vibration_data_hypertable(self):
        """Create the vibration_data table as a TimescaleDB hypertable"""
        # Create the table first
        create_table_query = sql.SQL("""
            CREATE TABLE IF NOT EXISTS {}.vibration_data (
                id BIGSERIAL,
                timestamp TIMESTAMPTZ NOT NULL,
                machine_id INTEGER REFERENCES {}.vibration_machines(id),
                program_file_id INTEGER,
                port VARCHAR(50) NOT NULL,
                origin VARCHAR(100),
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                contact_temperature DOUBLE PRECISION,
                v_peak_x DOUBLE PRECISION,
                v_peak_y DOUBLE PRECISION,
                v_peak_z DOUBLE PRECISION,
                v_rms_x DOUBLE PRECISION,
                v_rms_y DOUBLE PRECISION,
                v_rms_z DOUBLE PRECISION
            )
        """).format(sql.Identifier(self.config.schema), sql.Identifier(self.config.schema))

        with self.connection.cursor() as cursor:
            cursor.execute(create_table_query)

        self.connection.commit()

        # Convert to hypertable
        check_hypertable_query = sql.SQL("""
            SELECT EXISTS (
                SELECT 1
                FROM timescaledb_information.hypertables
                WHERE hypertable_schema = %s
                  AND hypertable_name = %s
            );
        """)

        with self.connection.cursor() as cursor:
            cursor.execute(check_hypertable_query, (self.config.schema, 'vibration_data'))
            is_hypertable = cursor.fetchone()[0]

            if not is_hypertable:
                table_name = f"{self.config.schema}.vibration_data"
                cursor.execute(f"SELECT create_hypertable('{table_name}', 'timestamp', if_not_exists => TRUE);")
                self.connection.commit()

    def insert_vibration_data(self, data_points: List[VibrationDataPoint]) -> int:
        """Insert vibration data points into PostgreSQL"""
        self.ensure_connection()
        if not data_points:
            return 0

        insert_query = sql.SQL("""
            INSERT INTO {}.vibration_data (
                timestamp,
                machine_id,
                program_file_id,
                port,
                origin,
                contact_temperature,
                v_peak_x,
                v_peak_y,
                v_peak_z,
                v_rms_x,
                v_rms_y,
                v_rms_z
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """).format(sql.Identifier(self.config.schema))

        inserted_count = 0

        with self.connection.cursor() as cursor:
            for data_point in data_points:
                cursor.execute(insert_query, data_point.to_postgres_tuple())
                inserted_count += 1

        self.connection.commit()
        return inserted_count

    def get_machine_id(self, machine_name: str) -> Optional[int]:
        """Get machine_id from machine_name"""
        self.ensure_connection()
        query = sql.SQL("""
            SELECT id FROM {}.vibration_machines WHERE machine_name = %s
        """).format(sql.Identifier(self.config.schema))

        with self.connection.cursor() as cursor:
            cursor.execute(query, (machine_name,))
            result = cursor.fetchone()
            return result[0] if result else None

    def fetch_sql_server_mct_data(self, sql_machine_id: int, start_date: Optional[datetime] = None) -> List[Dict]:
        """Fetch rows from sql_server_mct_data table for a specific machine_id"""
        self.ensure_connection()
        query = sql.SQL("""
            SELECT time, machine_id, machine_number, cycle_time, model, counter, created_at
            FROM {}.sql_server_mct_data
            WHERE machine_id = %s
        """).format(sql.Identifier(self.config.schema))

        params = [sql_machine_id]

        # Filter by start_date if provided
        if start_date:
            query = sql.SQL("""
                SELECT time, machine_id, machine_number, cycle_time, model, counter, created_at
                FROM {}.sql_server_mct_data
                WHERE machine_id = %s AND time >= %s
                ORDER BY time ASC
            """).format(sql.Identifier(self.config.schema))
            params.append(start_date)
        else:
            query = sql.SQL("""
                SELECT time, machine_id, machine_number, cycle_time, model, counter, created_at
                FROM {}.sql_server_mct_data
                WHERE machine_id = %s
                ORDER BY time ASC
            """).format(sql.Identifier(self.config.schema))

        with self.connection.cursor() as cursor:
            cursor.execute(query, params)
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            results = [dict(zip(columns, row)) for row in rows]
            return results

    def fetch_new_sql_server_mct_data(self, sql_machine_id: int, last_processed_time: datetime) -> List[Dict]:
        """Fetch new rows from sql_server_mct_data after a given time"""
        self.ensure_connection()
        query = sql.SQL("""
            SELECT time, cycle_time
            FROM {}.sql_server_mct_data
            WHERE machine_id = %s AND time > %s
            ORDER BY time ASC
        """).format(sql.Identifier(self.config.schema))

        with self.connection.cursor() as cursor:
            cursor.execute(query, (sql_machine_id, last_processed_time))
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            results = [dict(zip(columns, row)) for row in rows]
            return results

    def fetch_next_sql_server_mct_rows(self, sql_machine_id: int, current_time: datetime, limit: int = 5) -> List[Dict]:
        """Fetch next N rows from sql_server_mct_data after a given time"""
        self.ensure_connection()
        try:
            query = sql.SQL("""
                SELECT time, cycle_time
                FROM {}.sql_server_mct_data
                WHERE machine_id = %s AND time > %s
                ORDER BY time ASC
                LIMIT %s
            """).format(sql.Identifier(self.config.schema))

            with self.connection.cursor() as cursor:
                cursor.execute(query, (sql_machine_id, current_time, limit))
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                results = [dict(zip(columns, row)) for row in rows]
                return results
        except Exception as e:
            self.rollback()
            print(f"Error fetching next MCT rows: {e}")
            return []

    def fetch_vibration_parameters(self, machine_id: int, port: str) -> List[Dict]:
        """Fetch vibration parameters for a specific machine_id and port"""
        self.ensure_connection()
        query = sql.SQL("""
            SELECT id, machine_id, port, parameter_name, warning_limit, critical_limit
            FROM {}.vibration_parameters
            WHERE machine_id = %s AND port = %s
        """).format(sql.Identifier(self.config.schema))

        with self.connection.cursor() as cursor:
            cursor.execute(query, (machine_id, port))
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            results = [dict(zip(columns, row)) for row in rows]
            return results

    def fetch_parameter_limits(self, parameter_id: int) -> Optional[Dict]:
        """Fetch warning and critical limits for a specific parameter_id"""
        self.ensure_connection()
        try:
            query = sql.SQL("""
                SELECT id, warning_limit, critical_limit
                FROM {}.vibration_parameters
                WHERE id = %s
            """).format(sql.Identifier(self.config.schema))

            with self.connection.cursor() as cursor:
                cursor.execute(query, (parameter_id,))
                columns = [desc[0] for desc in cursor.description]
                row = cursor.fetchone()
                if row:
                    return dict(zip(columns, row))
                return None
        except Exception as e:
            self.rollback()
            print(f"Error fetching parameter limits for id {parameter_id}: {e}")
            return None

    def check_corrective_activity_exists(self, parameter_id: int, condition_id: int) -> Optional[Dict]:
        """Check if a corrective activity record exists for (machine_parameters_id, parameter_condition_id)"""
        self.ensure_connection()
        try:
            query = sql.SQL("""
                SELECT id, machine_parameters_id, parameter_condition_id, date_of_identification, recent_value,
                       latest_occurrence, number_of_occurrences
                FROM {}.corrective_activity
                WHERE machine_parameters_id = %s AND parameter_condition_id = %s
            """).format(sql.Identifier(self.config.schema))

            with self.connection.cursor() as cursor:
                cursor.execute(query, (parameter_id, condition_id))
                columns = [desc[0] for desc in cursor.description]
                row = cursor.fetchone()
                if row:
                    return dict(zip(columns, row))
                return None
        except Exception as e:
            self.rollback()
            print(f"Error checking corrective activity for param_id {parameter_id}, condition {condition_id}: {e}")
            return None

    def insert_corrective_activity(self, parameter_id: int, condition_id: int, recent_value: float, occurrence_time: datetime) -> int:
        """Insert a new corrective activity record"""
        self.ensure_connection()
        try:
            query = sql.SQL("""
                INSERT INTO {}.corrective_activity
                (machine_parameters_id, parameter_condition_id, date_of_identification, recent_value, latest_occurrence, number_of_occurrences)
                VALUES (%s, %s, %s, %s, %s, 1)
                RETURNING id
            """).format(sql.Identifier(self.config.schema))

            with self.connection.cursor() as cursor:
                cursor.execute(query, (parameter_id, condition_id, occurrence_time, recent_value, occurrence_time))
                activity_id = cursor.fetchone()[0]

            self.connection.commit()
            return activity_id
        except Exception as e:
            self.rollback()
            print(f"Error inserting corrective activity for param_id {parameter_id}: {e}")
            raise

    def update_corrective_activity(self, activity_id: int, recent_value: float, occurrence_time: datetime) -> None:
        """Update an existing corrective activity record"""
        self.ensure_connection()
        try:
            query = sql.SQL("""
                UPDATE {}.corrective_activity
                SET recent_value = %s,
                    latest_occurrence = %s,
                    number_of_occurrences = number_of_occurrences + 1
                WHERE id = %s
            """).format(sql.Identifier(self.config.schema))

            with self.connection.cursor() as cursor:
                cursor.execute(query, (recent_value, occurrence_time, activity_id))

            self.connection.commit()
        except Exception as e:
            self.rollback()
            print(f"Error updating corrective activity for activity_id {activity_id}: {e}")
            raise

    def close(self):
        """Close the PostgreSQL connection"""
        if self.connection and not self.connection.closed:
            self.connection.close()
            print("PostgreSQL connection closed.")

    def rollback(self):
        """Rollback the current transaction"""
        if self.connection:
            self.connection.rollback()
