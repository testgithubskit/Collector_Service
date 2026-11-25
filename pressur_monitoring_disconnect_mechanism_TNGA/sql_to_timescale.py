# import pyodbc
# import psycopg2
# from psycopg2.extras import execute_values
# import pandas as pd
# from datetime import datetime

# # SQL Server connection
# sql_conn = pyodbc.connect(
#     "DRIVER={ODBC Driver 17 for SQL Server};"
#     "SERVER=localhost\\SQLEXPRESS;"
#     "DATABASE=Machine_DB;"
#     "Trusted_Connection=yes;"
# )

# # PostgreSQL connection
# DATABASE_URL = "postgresql://postgres:siri2251105@localhost:5432/TOYOTA_MCM"
# pg_conn = psycopg2.connect(DATABASE_URL)
# pg_cursor = pg_conn.cursor()

# def create_hypertable():
#     """Create hypertable if not exists"""
#     try:
#         # Check if table already exists
#         check_table_query = """
#         SELECT EXISTS (
#             SELECT FROM information_schema.tables 
#             WHERE table_schema = 'public' 
#             AND table_name = 'mct_data'
#         );
#         """
#         pg_cursor.execute(check_table_query)
#         table_exists = pg_cursor.fetchone()[0]
        
#         if not table_exists:
#             # Create table with proper structure for hypertable
#             create_table_query = """
#             CREATE TABLE mct_data (
#                 time TIMESTAMPTZ NOT NULL,
#                 machine_number VARCHAR(50),
#                 cycle_time FLOAT,
#                 model INTEGER,
#                 counter INTEGER,
#                 created_at TIMESTAMPTZ DEFAULT NOW()
#             );
#             """
#             pg_cursor.execute(create_table_query)
            
#             # Create TimescaleDB hypertable with time as partitioning column
#             create_hypertable_query = "SELECT create_hypertable('mct_data', 'time');"
#             pg_cursor.execute(create_hypertable_query)
            
#             pg_conn.commit()
#             print("✅ Hypertable created successfully!")
#         else:
#             print("✅ Hypertable already exists")
        
#     except Exception as e:
#         print(f"❌ Error creating hypertable: {e}")
#         pg_conn.rollback()
#         raise

# def get_last_timestamp_postgres():
#     """Get the latest timestamp from PostgreSQL hypertable"""
#     try:
#         query = "SELECT MAX(time) AT TIME ZONE 'UTC' FROM mct_data"
#         pg_cursor.execute(query)
#         result = pg_cursor.fetchone()
        
#         if result and result[0]:
#             last_timestamp = result[0]
#             print(f"Last timestamp in PostgreSQL (UTC): {last_timestamp}")
#             return last_timestamp
#         else:
#             print("No data found in PostgreSQL table")
#             return None
            
#     except Exception as e:
#         print(f"Error getting last timestamp from PostgreSQL: {e}")
#         return None

# def fetch_sql_server_data():
#     """Fetch data from SQL Server MCT_Data table since last timestamp"""
#     try:
#         sql_cursor = sql_conn.cursor()
        
#         # Get last timestamp from PostgreSQL
#         last_timestamp = get_last_timestamp_postgres()
        
#         if last_timestamp:
#             # Fetch only records newer than last timestamp
#             query = """
#             SELECT 
#                 machine_number, 
#                 CONVERT(varchar, timestamp_timezone, 126) as timestamp_timezone,
#                 cycle_time, 
#                 model, 
#                 counter 
#             FROM MCT_Data 
#             WHERE timestamp_timezone > ?
#             ORDER BY timestamp_timezone
#             """
#             sql_cursor.execute(query, last_timestamp)
#         else:
#             # Fetch all data if no previous records
#             query = """
#             SELECT 
#                 machine_number, 
#                 CONVERT(varchar, timestamp_timezone, 126) as timestamp_timezone,
#                 cycle_time, 
#                 model, 
#                 counter 
#             FROM MCT_Data
#             ORDER BY timestamp_timezone
#             """
#             sql_cursor.execute(query)
        
#         # Fetch all rows
#         rows = sql_cursor.fetchall()
        
#         # Get column names
#         columns = [column[0] for column in sql_cursor.description]
        
#         # Create DataFrame
#         df = pd.DataFrame.from_records(rows, columns=columns)
        
#         # Convert timestamp string back to datetime
#         df['timestamp_timezone'] = pd.to_datetime(df['timestamp_timezone'])
        
#         sql_cursor.close()
        
#         if last_timestamp:
#             print(f"Found {len(df)} new records since {last_timestamp}")
#         else:
#             print(f"Found {len(df)} total records (initial sync)")
        
#         return df
        
#     except Exception as e:
#         print(f"Error fetching data from SQL Server: {e}")
#         raise

# def migrate_to_timescale(df):
#     """Migrate data to PostgreSQL TimescaleDB"""
#     try:
#         # Prepare data for insertion
#         data_to_insert = [
#             (
#                 row['timestamp_timezone'],  # time column (partitioning column)
#                 str(row['machine_number']),  # ensure machine_number is string
#                 float(row['cycle_time']),
#                 int(row['model']),
#                 int(row['counter'])
#             )
#             for _, row in df.iterrows()
#         ]
        
#         # Insert data using execute_values for better performance
#         insert_query = """
#         INSERT INTO mct_data (time, machine_number, cycle_time, model, counter)
#         VALUES %s
#         """
        
#         execute_values(pg_cursor, insert_query, data_to_insert)
#         pg_conn.commit()
        
#         print(f"✅ Successfully migrated {len(data_to_insert)} records to TimescaleDB!")
        
#     except Exception as e:
#         print(f"❌ Error migrating data to TimescaleDB: {e}")
#         pg_conn.rollback()
#         raise

# def main():
#     """Main incremental sync function"""
#     try:
#         print("Starting incremental sync from SQL Server to TimescaleDB...")
        
#         # Step 1: Create hypertable if not exists
#         create_hypertable()
        
#         # Step 2: Fetch new data from SQL Server since last sync
#         df = fetch_sql_server_data()
        
#         if df.empty:
#             print("No new records to sync")
#             return
        
#         # Step 3: Migrate new data to TimescaleDB
#         migrate_to_timescale(df)
        
#         print(f"Incremental sync completed successfully! Synced {len(df)} new records.")
        
#     except Exception as e:
#         print(f"Sync failed: {e}")
        
#     finally:
#         # Close connections
#         if 'sql_conn' in locals():
#             sql_conn.close()
#         if 'pg_conn' in locals():
#             pg_conn.close()
#         print("All connections closed")

# if __name__ == "__main__":
#     main()







#not linked the machine_id column with machine table

# import pyodbc
# import psycopg2
# from psycopg2.extras import execute_values
# import pandas as pd
# from datetime import datetime

# # SQL Server connection
# sql_conn = pyodbc.connect(
#     "DRIVER={ODBC Driver 17 for SQL Server};"
#     "SERVER=localhost\\SQLEXPRESS;"
#     "DATABASE=Machine_DB;"
#     "Trusted_Connection=yes;"
# )

# # Remote PostgreSQL / TimescaleDB connection
# DATABASE_URL = "postgresql://postgres:1234@172.18.100.87:5432/Toyota_Demo"

# pg_conn = psycopg2.connect(DATABASE_URL)
# pg_cursor = pg_conn.cursor()

# # Schema and table names
# SCHEMA_NAME = "tiei_sample_5"
# TABLE_NAME = "SQL_SERVER_MCT_DATA"

# def create_hypertable():
#     """Create schema, table, and hypertable if not exists"""
    
#     try:
#         # Create schema if not exists
#         create_schema_query = f"""
#         CREATE SCHEMA IF NOT EXISTS {SCHEMA_NAME};
#         """
#         pg_cursor.execute(create_schema_query)

#         # Check if table exists
#         check_table_query = f"""
#         SELECT EXISTS (
#             SELECT FROM information_schema.tables 
#             WHERE table_schema = '{SCHEMA_NAME}'
#             AND table_name = '{TABLE_NAME}'
#         );
#         """

#         pg_cursor.execute(check_table_query)
#         table_exists = pg_cursor.fetchone()[0]

#         if not table_exists:

#             # Create table
#             create_table_query = f"""
#             CREATE TABLE {SCHEMA_NAME}.{TABLE_NAME} (
#                 time TIMESTAMPTZ NOT NULL,
#                 machine_number VARCHAR(50),
#                 cycle_time FLOAT,
#                 model INTEGER,
#                 counter INTEGER,
#                 created_at TIMESTAMPTZ DEFAULT NOW()
#             );
#             """

#             pg_cursor.execute(create_table_query)

#             # Create hypertable
#             create_hypertable_query = f"""
#             SELECT create_hypertable(
#                 '{SCHEMA_NAME}.{TABLE_NAME}',
#                 'time'
#             );
#             """

#             pg_cursor.execute(create_hypertable_query)

#             pg_conn.commit()

#             print("✅ Hypertable created successfully!")

#         else:
#             print("✅ Hypertable already exists")

#     except Exception as e:
#         print(f"❌ Error creating hypertable: {e}")
#         pg_conn.rollback()
#         raise


# def get_last_timestamp_postgres():
#     """Get latest timestamp from PostgreSQL"""

#     try:
#         query = f"""
#         SELECT MAX(time) AT TIME ZONE 'UTC'
#         FROM {SCHEMA_NAME}.{TABLE_NAME}
#         """

#         pg_cursor.execute(query)

#         result = pg_cursor.fetchone()

#         if result and result[0]:

#             last_timestamp = result[0]

#             print(f"Last timestamp in PostgreSQL (UTC): {last_timestamp}")

#             return last_timestamp

#         else:
#             print("No data found in PostgreSQL table")
#             return None

#     except Exception as e:
#         print(f"Error getting last timestamp from PostgreSQL: {e}")
#         return None


# def fetch_sql_server_data():
#     """Fetch new data from SQL Server"""

#     try:
#         sql_cursor = sql_conn.cursor()

#         # Get last synced timestamp
#         last_timestamp = get_last_timestamp_postgres()

#         if last_timestamp:

#             # Incremental sync
#             query = """
#             SELECT 
#                 machine_number,
#                 CONVERT(varchar, timestamp_timezone, 126) as timestamp_timezone,
#                 cycle_time,
#                 model,
#                 counter
#             FROM MCT_Data
#             WHERE timestamp_timezone > ?
#             ORDER BY timestamp_timezone
#             """

#             sql_cursor.execute(query, last_timestamp)

#         else:

#             # Initial sync
#             query = """
#             SELECT 
#                 machine_number,
#                 CONVERT(varchar, timestamp_timezone, 126) as timestamp_timezone,
#                 cycle_time,
#                 model,
#                 counter
#             FROM MCT_Data
#             ORDER BY timestamp_timezone
#             """

#             sql_cursor.execute(query)

#         # Fetch rows
#         rows = sql_cursor.fetchall()

#         # Column names
#         columns = [column[0] for column in sql_cursor.description]

#         # Create DataFrame
#         df = pd.DataFrame.from_records(rows, columns=columns)

#         # Convert timestamp
#         if not df.empty:
#             df['timestamp_timezone'] = pd.to_datetime(
#                 df['timestamp_timezone']
#             )

#         sql_cursor.close()

#         if last_timestamp:
#             print(f"Found {len(df)} new records since {last_timestamp}")
#         else:
#             print(f"Found {len(df)} total records (initial sync)")

#         return df

#     except Exception as e:
#         print(f"Error fetching data from SQL Server: {e}")
#         raise


# def migrate_to_timescale(df):
#     """Insert data into TimescaleDB"""

#     try:

#         data_to_insert = [
#             (
#                 row['timestamp_timezone'],
#                 str(row['machine_number']),
#                 float(row['cycle_time']),
#                 int(row['model']),
#                 int(row['counter'])
#             )
#             for _, row in df.iterrows()
#         ]

#         insert_query = f"""
#         INSERT INTO {SCHEMA_NAME}.{TABLE_NAME}
#         (
#             time,
#             machine_number,
#             cycle_time,
#             model,
#             counter
#         )
#         VALUES %s
#         """

#         execute_values(
#             pg_cursor,
#             insert_query,
#             data_to_insert
#         )

#         pg_conn.commit()

#         print(
#             f"✅ Successfully migrated "
#             f"{len(data_to_insert)} records "
#             f"to TimescaleDB!"
#         )

#     except Exception as e:

#         print(f"❌ Error migrating data to TimescaleDB: {e}")

#         pg_conn.rollback()

#         raise


# def main():
#     """Main sync function"""

#     try:

#         print(
#             "Starting incremental sync "
#             "from SQL Server to TimescaleDB..."
#         )

#         # Step 1
#         create_hypertable()

#         # Step 2
#         df = fetch_sql_server_data()

#         if df.empty:
#             print("No new records to sync")
#             return

#         # Step 3
#         migrate_to_timescale(df)

#         print(
#             f"Incremental sync completed successfully! "
#             f"Synced {len(df)} new records."
#         )

#     except Exception as e:

#         print(f"Sync failed: {e}")

#     finally:

#         # Close connections
#         if 'sql_conn' in locals():
#             sql_conn.close()

#         if 'pg_conn' in locals():
#             pg_conn.close()

#         print("All connections closed")


# if __name__ == "__main__":
#     main()







# import pyodbc
# import psycopg2
# from psycopg2.extras import execute_values
# import pandas as pd
# from datetime import datetime
# import time

# # SQL Server connection
# sql_conn = pyodbc.connect(
#     "DRIVER={ODBC Driver 17 for SQL Server};"
#     "SERVER=localhost\\SQLEXPRESS;"
#     "DATABASE=Machine_DB;"
#     "Trusted_Connection=yes;"
# )

# # PostgreSQL connection
# DATABASE_URL = "postgresql://postgres:1234@172.18.100.87:5432/Toyota_Demo"

# pg_conn = psycopg2.connect(DATABASE_URL)
# pg_cursor = pg_conn.cursor()

# # Schema and table names
# SCHEMA_NAME = "tiei_sample_5"
# TABLE_NAME = "sql_server_mct_data"

# # Machine mapping
# # SQL Server machine_number -> PostgreSQL machines.id
# MACHINE_MAPPING = {
#     "Machine_1": 1,
#     "Machine_2": 2,
#     "Machine_3": 3,
#     "Machine_5": 5,
#     "Machine_6": 6,
#     "Machine_7": 7,
#     "Machine_8": 8,
#     "Machine_9": 9,
#     "Machine_10": 10,
#     "Machine_11": 11,
#     "Machine_12": 12,
#     "Machine_13": 13,
#     "Machine_14": 14,
#     "Machine_15": 15,
#     "Machine_16": 16,
#     "Machine_17": 17,
#     "Machine_18": 18,
#     "Machine_19": 19,
#     "Machine_20": 20,
#     "Machine_21": 21
# }


# def create_table():
#     """Create schema and table if not exists"""

#     try:

#         # Create schema
#         create_schema_query = f"""
#         CREATE SCHEMA IF NOT EXISTS {SCHEMA_NAME};
#         """

#         pg_cursor.execute(create_schema_query)

#         # Check table existence
#         check_table_query = f"""
#         SELECT EXISTS (
#             SELECT FROM information_schema.tables
#             WHERE table_schema = '{SCHEMA_NAME}'
#             AND table_name = LOWER('{TABLE_NAME}')
#         );
#         """

#         pg_cursor.execute(check_table_query)

#         table_exists = pg_cursor.fetchone()[0]

#         if not table_exists:

#             create_table_query = f"""
#             CREATE TABLE {SCHEMA_NAME}.{TABLE_NAME} (
#                 time TIMESTAMP NOT NULL,
#                 machine_id INTEGER,
#                 machine_number VARCHAR(50),
#                 cycle_time FLOAT,
#                 model INTEGER,
#                 counter INTEGER,
#                 created_at TIMESTAMPTZ DEFAULT NOW(),

#                 CONSTRAINT fk_machine
#                 FOREIGN KEY (machine_id)
#                 REFERENCES {SCHEMA_NAME}.machines(id)
#             );
#             """

#             pg_cursor.execute(create_table_query)

#             pg_conn.commit()

#             print("✅ Table created successfully!")

#         else:
#             print("✅ Table already exists")

#     except Exception as e:

#         print(f"❌ Error creating table: {e}")

#         pg_conn.rollback()

#         raise


# def get_last_timestamp_postgres():
#     """Get latest timestamp from PostgreSQL"""

#     try:

#         query = f"""
#         SELECT MAX(time)
#         FROM {SCHEMA_NAME}.{TABLE_NAME}
#         """

#         pg_cursor.execute(query)

#         result = pg_cursor.fetchone()

#         if result and result[0]:

#             last_timestamp = result[0]

#             print(
#                 f"Last timestamp in PostgreSQL (UTC): "
#                 f"{last_timestamp}"
#             )

#             return last_timestamp

#         else:

#             print("No data found in PostgreSQL table")

#             return None

#     except Exception as e:

#         print(
#             f"Error getting last timestamp "
#             f"from PostgreSQL: {e}"
#         )

#         return None


# def fetch_sql_server_data():
#     """Fetch new data from SQL Server"""

#     try:

#         sql_cursor = sql_conn.cursor()

#         # Get last synced timestamp
#         last_timestamp = get_last_timestamp_postgres()

#         if last_timestamp:

#             # Incremental sync
#             query = """
#             SELECT
#                 machine_number,
#                 CONVERT(varchar(33), timestamp_timezone, 126)
#                   as timestamp_timezone,
#                 cycle_time,
#                 model,
#                 counter
#             FROM MCT_Data
#             WHERE timestamp_timezone > ?
#             ORDER BY timestamp_timezone
#             """

#             sql_cursor.execute(query, last_timestamp)

#         else:

#             # Initial sync
#             query = """
#             SELECT
#                 machine_number,
#                 CONVERT(varchar(33), timestamp_timezone, 126)
#                   as timestamp_timezone,
#                 cycle_time,
#                 model,
#                 counter
#             FROM MCT_Data
#             ORDER BY timestamp_timezone
#             """

#             sql_cursor.execute(query)

#         # Fetch rows
#         rows = sql_cursor.fetchall()

#         # Column names
#         columns = [
#             column[0]
#             for column in sql_cursor.description
#         ]

#         # DataFrame
#         df = pd.DataFrame.from_records(
#             rows,
#             columns=columns
#         )

#         # Convert timestamp
#         if not df.empty:

#             df['timestamp_timezone'] = pd.to_datetime(
#                 df['timestamp_timezone'],
#                 utc=True
#             ).dt.tz_convert(None)

#         sql_cursor.close()

#         if last_timestamp:

#             print(
#                 f"Found {len(df)} new records "
#                 f"since {last_timestamp}"
#             )

#         else:

#             print(
#                 f"Found {len(df)} total records "
#                 f"(initial sync)"
#             )

#         return df

#     except Exception as e:

#         print(
#             f"Error fetching data "
#             f"from SQL Server: {e}"
#         )

#         raise


# def migrate_to_postgres(df):
#     """Insert data into PostgreSQL"""

#     try:

#         data_to_insert = []

#         for _, row in df.iterrows():

#             machine_number = str(row['machine_number'])

#             # Get machine_id from mapping
#             machine_id = MACHINE_MAPPING.get(machine_number)

#             # Skip unmapped machines
#             if machine_id is None:

#                 print(
#                     f"⚠ No mapping found for "
#                     f"{machine_number}"
#                 )

#                 continue

#             data_to_insert.append(
#                 (
#                     row['timestamp_timezone'],
#                     machine_id,
#                     machine_number,
#                     float(row['cycle_time']),
#                     int(row['model']),
#                     int(row['counter'])
#                 )
#             )

#         if not data_to_insert:

#             print("No valid data to insert")

#             return

#         insert_query = f"""
#         INSERT INTO {SCHEMA_NAME}.{TABLE_NAME}
#         (
#             time,
#             machine_id,
#             machine_number,
#             cycle_time,
#             model,
#             counter
#         )
#         VALUES %s
#         """

#         execute_values(
#             pg_cursor,
#             insert_query,
#             data_to_insert
#         )

#         pg_conn.commit()

#         print(
#             f"✅ Successfully migrated "
#             f"{len(data_to_insert)} records!"
#         )

#     except Exception as e:

#         print(f"❌ Error migrating data: {e}")

#         pg_conn.rollback()

#         raise

# def main():
#     """Continuous sync every 60 seconds"""

#     try:

#         print(
#             "Starting continuous incremental sync "
#             "from SQL Server to PostgreSQL..."
#         )

#         # Create table once
#         create_table()

#         while True:

#             try:

#                 print(
#                     "\nChecking for new records..."
#                 )

#                 # Fetch new records
#                 df = fetch_sql_server_data()

#                 if df.empty:

#                     print(
#                         "No new records found"
#                     )

#                 else:

#                     # Insert records
#                     migrate_to_postgres(df)

#                     print(
#                         f"Incremental sync completed! "
#                         f"Synced {len(df)} records."
#                     )

#             except Exception as sync_error:

#                 print(
#                     f"Error during sync cycle: "
#                     f"{sync_error}"
#                 )

#             # Wait 60 seconds
#             print(
#                 "Waiting 60 seconds for next sync..."
#             )

#             time.sleep(60)

#     except KeyboardInterrupt:

#         print(
#             "\nSync stopped manually by user"
#         )

#     except Exception as e:

#         print(f"Fatal error: {e}")

#     finally:

#         # Close connections
#         if 'sql_conn' in locals():
#             sql_conn.close()

#         if 'pg_conn' in locals():
#             pg_conn.close()

#         print("All connections closed")


# if __name__ == "__main__":
#     main()





import time

from database import (
    sql_conn,
    pg_conn,
    
)

from utils import (
    create_table,
    fetch_sql_server_data,
    migrate_to_postgres
)

def main():

    try:

        print(
            "Starting continuous incremental sync "
            "from SQL Server to PostgreSQL..."
        )

        create_table()

        while True:

            try:

                print(
                    "\nChecking for new records..."
                )

                df = fetch_sql_server_data(
                    sql_conn
                )

                if df.empty:

                    print(
                        "No new records found"
                    )

                else:

                    migrate_to_postgres(df)

                    print(
                        f"Incremental sync completed! "
                        f"Synced {len(df)} records."
                    )

            except Exception as sync_error:

                print(
                    f"Error during sync cycle: "
                    f"{sync_error}"
                )

            print(
                "Waiting 60 seconds for next sync..."
            )

            time.sleep(60)

    except KeyboardInterrupt:

        print(
            "\nSync stopped manually by user"
        )

    finally:

        sql_conn.close()

        pg_conn.close()

        print("All connections closed")


if __name__ == "__main__":
    main()