# from pymongo import MongoClient
import psycopg2
# import pyodbc
import os

from config import (
    DATABASE_URL,
    # SQL_SERVER_CONNECTION_STRING,
    POSTGRES_HOST,
    POSTGRES_PORT,
    POSTGRES_DATABASE,
    POSTGRES_USER,
    POSTGRES_PASSWORD,
    # MONGODB_URL
)

from pony.orm import *

from models import db
# MongoDB Connection
# mongo_client = MongoClient(MONGODB_URL)
# # mongo_client = MongoClient("mongodb://host.docker.internal:27017")

# mongo_db = mongo_client["MTLINKi"]

# collection = mongo_db["L1Signal_Pool_Active"]

# Verify MongoDB connection
# try:
#     mongo_client.admin.command('ping')
#     print("[DB] ✅ MongoDB connected successfully.")
# except Exception as _mongo_err:
#     print(f"[DB] ❌ MongoDB connection failed: {_mongo_err}")
#     raise

# PostgreSQL Connection
pg_conn = psycopg2.connect(DATABASE_URL)

pg_cursor = pg_conn.cursor()

print(f"[DB] ✅ PostgreSQL connected successfully → {POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DATABASE}")

# sql_conn = pyodbc.connect(
#     SQL_SERVER_CONNECTION_STRING
# )


db.bind(
    provider="postgres",
    user=POSTGRES_USER,
    password=POSTGRES_PASSWORD,
    host=POSTGRES_HOST,
    database=POSTGRES_DATABASE,
    port=POSTGRES_PORT
)

db.generate_mapping(
    create_tables=True
)


def create_pressure_sensor_hypertable():
    try:
        # Create table if it doesn't exist
        pg_cursor.execute("""
            CREATE TABLE IF NOT EXISTS tiei_sample_4.pressure_sensor_data (
                
                "timestamp" TIMESTAMP NOT NULL,
                pressure_value DOUBLE PRECISION,
                created_at TIMESTAMP DEFAULT NOW(),
                machine_id INTEGER REFERENCES tiei_sample_4.pressure_monitoring_machine(id),
                log_file_id INTEGER REFERENCES tiei_sample_4.pressure_log_file(id)
            );
        """)
        pg_conn.commit()

        # Check whether it's already a hypertable
        pg_cursor.execute("""
            SELECT EXISTS (
                SELECT 1
                FROM timescaledb_information.hypertables
                WHERE hypertable_schema = 'tiei_sample_4'
                  AND hypertable_name = 'pressure_sensor_data'
            );
        """)

        exists = pg_cursor.fetchone()[0]

        if not exists:
            print("Creating pressure_sensor_data hypertable...")

            pg_cursor.execute("""
                SELECT create_hypertable(
                    'tiei_sample_4.pressure_sensor_data',
                    'timestamp',
                    if_not_exists => TRUE
                );
            """)

            pg_conn.commit()
            print("Hypertable created successfully.")
        else:
            print("pressure_sensor_data is already a hypertable.")

    except Exception as e:
        pg_conn.rollback()
        print(f"Error creating hypertable: {e}")

def initialize_pressure_monitoring_machines():
    try:
        # Check if records already exist
        pg_cursor.execute("""
            SELECT COUNT(*)
            FROM tiei_sample_4.pressure_monitoring_machine;
        """)

        count = pg_cursor.fetchone()[0]

        if count == 0:
            print("Inserting default pressure monitoring machines...")

            pg_cursor.execute("""
                INSERT INTO tiei_sample_4.pressure_monitoring_machine
                    (machine_name, warning_limit, critical_limit, status)
                VALUES
                    ('2nd Rough', 10.0, 15.0, 'ACTIVE'),
                    ('4th Finish', 10.0, 15.0, 'ACTIVE');
            """)

            pg_conn.commit()
            print("Default machine records inserted.")
        else:
            print("pressure_monitoring_machine already initialized.")

    except Exception as e:
        pg_conn.rollback()
        print(f"Error initializing pressure_monitoring_machine: {e}")

def init_disconnect_tables():
    try:
        # Check if cycle_time_limits has data
        pg_cursor.execute("SELECT COUNT(*) FROM tiei_sample_4.cycle_time_limits;")
        count = pg_cursor.fetchone()[0]
        if count == 0:
            print("Inserting default values into cycle_time_limits...")
            pg_cursor.execute("""
                INSERT INTO tiei_sample_4.cycle_time_limits (id, machine_id, warning_limit, critical_limit, status) VALUES
                (1, 1, 60, 90, 'ACTIVE'),
                (2, 2, 59.74, 90.79, 'NOT_DISCONNECTED'),
                (3, 3, 65.92, 103.13, 'NOT_DISCONNECTED'),
                (4, 5, 55.97, 90.79, 'NOT_DISCONNECTED'),
                (5, 6, 53.09, 76.49, 'NOT_DISCONNECTED'),
                (6, 7, 67.1, 89.54, 'NOT_DISCONNECTED'),
                (7, 8, 64.6, 102, 'NOT_DISCONNECTED'),
                (8, 9, 59.58, 99.58, 'NOT_DISCONNECTED'),
                (9, 10, 58.22, 95.08, 'NOT_DISCONNECTED'),
                (10, 11, 58.45, 81.18, 'NOT_DISCONNECTED'),
                (11, 12, 50.3, 75.86, 'NOT_DISCONNECTED'),
                (12, 13, 62.96, 83.38, 'NOT_DISCONNECTED'),
                (13, 14, 67.67, 88.84, 'NOT_DISCONNECTED'),
                (14, 15, 65.25, 95.59, 'NOT_DISCONNECTED'),
                (15, 16, 60.46, 87.83, 'NOT_DISCONNECTED'),
                (16, 17, 62.55, 92.36, 'NOT_DISCONNECTED'),
                (17, 18, 60.37, 96.65, 'NOT_DISCONNECTED'),
                (18, 19, 69.33, 89.41, 'NOT_DISCONNECTED'),
                (19, 20, 60.67, 92.4, 'NOT_DISCONNECTED'),
                (20, 21, 61.65, 96.73, 'NOT_DISCONNECTED'),
                (21, 22, 60, 90, 'NOT_DISCONNECTED'),
                (22, 23, 59.74, 90.79, 'NOT_DISCONNECTED'),
                (23, 24, 65.92, 103.13, 'NOT_DISCONNECTED'),
                (24, 25, 55.97, 90.79, 'NOT_DISCONNECTED'),
                (25, 26, 53.09, 76.49, 'NOT_DISCONNECTED'),
                (26, 27, 67.1, 89.54, 'NOT_DISCONNECTED'),
                (27, 28, 64.6, 102, 'NOT_DISCONNECTED'),
                (28, 29, 59.58, 99.58, 'NOT_DISCONNECTED'),
                (29, 30, 58.22, 95.08, 'NOT_DISCONNECTED'),
                (30, 31, 58.45, 81.18, 'NOT_DISCONNECTED'),
                (31, 32, 50.3, 75.86, 'NOT_DISCONNECTED'),
                (32, 33, 62.96, 83.38, 'NOT_DISCONNECTED'),
                (33, 34, 67.67, 88.84, 'NOT_DISCONNECTED'),
                (34, 35, 65.25, 95.59, 'NOT_DISCONNECTED'),
                (35, 36, 60.46, 87.83, 'NOT_DISCONNECTED'),
                (36, 37, 62.55, 92.36, 'NOT_DISCONNECTED'),
                (37, 38, 60.37, 96.65, 'NOT_DISCONNECTED'),
                (38, 39, 69.33, 89.41, 'NOT_DISCONNECTED'),
                (39, 40, 60.67, 92.4, 'NOT_DISCONNECTED'),
                (40, 41, 61.65, 96.73, 'NOT_DISCONNECTED'),
                (41, 42, 60, 90, 'DISCONNECTED'),
                (42, 43, 59.74, 90.79, 'DISCONNECTED'),
                (43, 44, 65.92, 103.13, 'DISCONNECTED'),
                (44, 45, 55.97, 90.79, 'NOT_DISCONNECTED'),
                (45, 46, 53.09, 76.49, 'DISCONNECTED'),
                (46, 47, 67.1, 89.54, 'DISCONNECTED'),
                (47, 48, 64.6, 102, 'NOT_DISCONNECTED'),
                (48, 49, 59.58, 99.58, 'NOT_DISCONNECTED'),
                (49, 50, 58.22, 95.08, 'NOT_DISCONNECTED'),
                (50, 51, 58.45, 81.18, 'NOT_DISCONNECTED'),
                (51, 52, 50.3, 75.86, 'NOT_DISCONNECTED'),
                (52, 53, 62.96, 83.38, 'NOT_DISCONNECTED'),
                (53, 54, 67.67, 88.84, 'NOT_DISCONNECTED'),
                (54, 55, 65.25, 95.59, 'NOT_DISCONNECTED'),
                (55, 56, 60.46, 87.83, 'NOT_DISCONNECTED'),
                (56, 57, 62.55, 92.36, 'NOT_DISCONNECTED'),
                (57, 58, 60.37, 96.65, 'NOT_DISCONNECTED'),
                (58, 59, 69.33, 89.41, 'NOT_DISCONNECTED'),
                (59, 60, 60.67, 92.4, 'NOT_DISCONNECTED'),
                (60, 61, 61.65, 96.73, 'ACTIVE'),
                (61, 62, 60, 90, 'ACTIVE'),
                (62, 63, 59.74, 90.79, 'ACTIVE'),
                (63, 64, 65.92, 103.13, 'ACTIVE'),
                (64, 4, 55.97, 90.79, 'NOT_DISCONNECTED');
            """)
            
            # Update sequence since we inserted explicit IDs
            pg_cursor.execute("SELECT setval(pg_get_serial_sequence('tiei_sample_4.cycle_time_limits', 'id'), coalesce(max(id),0) + 1, false) FROM tiei_sample_4.cycle_time_limits;")
            pg_conn.commit()
            print("Default values inserted into cycle_time_limits.")
        else:
            print("cycle_time_limits already has data.")

        # Create disconnection_history1 table and hypertable
        pg_cursor.execute("""
            CREATE TABLE IF NOT EXISTS tiei_sample_4.disconnection_history1 (
                id SERIAL,
                machine_id INTEGER REFERENCES tiei_sample_4.machines(id),
                status VARCHAR(50),
                start_time TIMESTAMPTZ NOT NULL,
                stop_time TIMESTAMPTZ
            );
        """)
        pg_conn.commit()

        # Check whether it's already a hypertable
        pg_cursor.execute("""
            SELECT EXISTS (
                SELECT 1
                FROM timescaledb_information.hypertables
                WHERE hypertable_schema = 'tiei_sample_4'
                  AND hypertable_name = 'disconnection_history1'
            );
        """)
        exists = pg_cursor.fetchone()[0]
        
        if not exists:
            print("Creating disconnection_history1 hypertable...")
            pg_cursor.execute("""
                SELECT create_hypertable(
                    'tiei_sample_4.disconnection_history1',
                    'start_time',
                    if_not_exists => TRUE
                );
            """)
            pg_conn.commit()
            print("Hypertable disconnection_history1 created successfully.")
        else:
            print("disconnection_history1 is already a hypertable.")

    except Exception as e:
        pg_conn.rollback()
        print(f"Error initializing disconnect tables: {e}")


#uncomment for pressure_data_shared
# <-- CALL IT HERE
INIT_DB = os.getenv("INIT_DB", "false").lower() == "true"

if INIT_DB:
    print("Initializing database...")
    create_pressure_sensor_hypertable()
    
    # Ensure latest_time column exists in case the table was already created by Pony ORM
    try:
        pg_cursor.execute("ALTER TABLE tiei_sample_4.pressure_log_file ADD COLUMN IF NOT EXISTS latest_time TIMESTAMP;")
        pg_conn.commit()
    except Exception as e:
        pg_conn.rollback()
        print(f"Error adding latest_time column: {e}")

    initialize_pressure_monitoring_machines()
    print("Database initialization completed.")
else:
    print("Skipping database initialization.")