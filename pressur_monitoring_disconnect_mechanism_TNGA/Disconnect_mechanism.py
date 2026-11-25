












# from pymongo import MongoClient
# import psycopg2
# import time

# # -------------------------
# # MongoDB Connection
# # -------------------------
# mongo_client = MongoClient("mongodb://localhost:27017")

# mongo_db = mongo_client["MtLinki"]
# collection = mongo_db["L1Signal_Pool_Active"]

# # -------------------------
# # PostgreSQL Connection
# # -------------------------
# DATABASE_URL = "postgresql://postgres:1234@172.18.100.87:5432/Toyota_Demo"
# SCHEMA_NAME = "tiei_sample_5"

# pg_conn = psycopg2.connect(DATABASE_URL)
# pg_cursor = pg_conn.cursor()

# # -------------------------
# # Machine Mapping
# # -------------------------
# machine_map = {
#     "T_B_OP160": 2,
#     "T_B_OP180": 3,
#     "T_B_OP195A": 4,
#     "T_B_OP195B": 5,
#     "T_B_OP230": 6,
#     "T_B_OP235": 7,
#     "T_B_OP540": 8,
#     "T_C_OP10": 9,
#     "T_C_OP100": 10,
#     "T_C_OP160": 11,
#     "T_C_OP190": 12,
#     "T_C_OP30": 13,
#     "T_C_OP40": 14,
#     "T_C_OP90": 15,
#     "T_C_OP910": 16,
#     "T_C_OP911": 17,
#     "T_C_OP912": 18,
#     "T_C_OP913": 19,
#     "T_C_OP914": 20,
#     "T_C_OP915": 21,
#     "T_C_OP916": 22,
#     "T_H_OP10": 23,
#     "T_H_OP100A": 24,
#     "T_H_OP100B": 25,
#     "T_H_OP110A": 26,
#     "T_H_OP110B": 27,
#     "T_H_OP120A": 28,
#     "T_H_OP120B": 29,
#     "T_H_OP140A": 30,
#     "T_H_OP140B": 31,
#     "T_H_OP150A": 32,
#     "T_H_OP150B": 33,
#     "T_H_OP160A": 34,
#     "T_H_OP160B": 35,
#     "T_H_OP170A": 36,
#     "T_H_OP170B": 37,
#     "T_H_OP180A": 38,
#     "T_H_OP180B": 39,
#     "T_H_OP20": 40,
#     "T_H_OP230": 41,
#     "T_H_OP240": 42,
#     "T_H_OP250": 43,
#     "T_H_OP260": 44,
#     "T_H_OP270": 45,
#     "T_H_OP280": 46,
#     "T_H_OP285": 47,
#     "T_H_OP300": 48,
#     "T_H_OP50": 49,
#     "T_H_OP500": 50,
#     "T_H_OP510": 51,
#     "T_H_OP520": 52,
#     "T_H_OP530": 53,
#     "T_H_OP540": 54,
#     "T_H_OP55": 55,
#     "T_H_OP550": 56,
#     "T_H_OP80A": 57,
#     "T_H_OP80B": 58,
#     "T_H_OP90A": 59,
#     "T_H_OP90B": 60
# }

# update_query = f"""
# UPDATE {SCHEMA_NAME}.cycle_time_limits
# SET status = %s
# WHERE machine_id = %s
# """

# try:

#     while True:

#         print("\n========================================")
#         print("Checking MongoDB DISCONNECT status...")
#         print("========================================")

#         updated_count = 0

#         cursor = collection.find(
#             {
#                 "L1Name": {"$in": list(machine_map.keys())},
#                 "signalname": "DISCONNECT"
#             },
#             {
#                 "_id": 0,
#                 "L1Name": 1,
#                 "value": 1
#             }
#         )

#         for doc in cursor:

#             machine_name = doc["L1Name"]
#             machine_id = machine_map[machine_name]
#             value = doc["value"]

#             status = (
#                 "DISCONNECTED"
#                 if value is True
#                 else "NOT_DISCONNECTED"
#             )

#             pg_cursor.execute(
#                 update_query,
#                 (status, machine_id)
#             )

#             if pg_cursor.rowcount > 0:

#                 updated_count += pg_cursor.rowcount

#                 print(
#                     f"Updated Machine: {machine_name} "
#                     f"(ID={machine_id}) "
#                     f"Status={status}"
#                 )

#             else:

#                 print(
#                     f"Machine ID {machine_id} not found in cycle_time_limits"
#                 )

#         pg_conn.commit()

#         print(
#             f"\nCycle Completed Successfully "
#             f"({updated_count} machines updated)"
#         )

#         # Wait 5 seconds before next query
#         time.sleep(5)

# except KeyboardInterrupt:

#     print("\nStopping disconnect monitoring...")

# except Exception as e:

#     print(f"\nError: {e}")
#     pg_conn.rollback()

# finally:

#     pg_cursor.close()
#     pg_conn.close()
#     mongo_client.close()

#     print("Connections closed.")











#to save for history table === disconnection_history


# from pymongo import MongoClient
# import psycopg2
# import time

# # -------------------------
# # MongoDB Connection
# # -------------------------
# mongo_client = MongoClient("mongodb://localhost:27017")

# mongo_db = mongo_client["MtLinki"]
# collection = mongo_db["L1Signal_Pool_Active"]

# # -------------------------
# # PostgreSQL Connection
# # -------------------------
# DATABASE_URL = "postgresql://postgres:1234@172.18.100.87:5432/Toyota_Demo"
# SCHEMA_NAME = "tiei_sample_5"

# pg_conn = psycopg2.connect(DATABASE_URL)
# pg_cursor = pg_conn.cursor()

# # -------------------------
# # Machine Mapping
# # -------------------------
# machine_map = {
#     "T_B_OP160": 2,
#     "T_B_OP180": 3,
#     "T_B_OP195A": 4,
#     "T_B_OP195B": 5,
#     "T_B_OP230": 6,
#     "T_B_OP235": 7,
#     "T_B_OP540": 8,
#     "T_C_OP10": 9,
#     "T_C_OP100": 10,
#     "T_C_OP160": 11,
#     "T_C_OP190": 12,
#     "T_C_OP30": 13,
#     "T_C_OP40": 14,
#     "T_C_OP90": 15,
#     "T_C_OP910": 16,
#     "T_C_OP911": 17,
#     "T_C_OP912": 18,
#     "T_C_OP913": 19,
#     "T_C_OP914": 20,
#     "T_C_OP915": 21,
#     "T_C_OP916": 22,
#     "T_H_OP10": 23,
#     "T_H_OP100A": 24,
#     "T_H_OP100B": 25,
#     "T_H_OP110A": 26,
#     "T_H_OP110B": 27,
#     "T_H_OP120A": 28,
#     "T_H_OP120B": 29,
#     "T_H_OP140A": 30,
#     "T_H_OP140B": 31,
#     "T_H_OP150A": 32,
#     "T_H_OP150B": 33,
#     "T_H_OP160A": 34,
#     "T_H_OP160B": 35,
#     "T_H_OP170A": 36,
#     "T_H_OP170B": 37,
#     "T_H_OP180A": 38,
#     "T_H_OP180B": 39,
#     "T_H_OP20": 40,
#     "T_H_OP230": 41,
#     "T_H_OP240": 42,
#     "T_H_OP250": 43,
#     "T_H_OP260": 44,
#     "T_H_OP270": 45,
#     "T_H_OP280": 46,
#     "T_H_OP285": 47,
#     "T_H_OP300": 48,
#     "T_H_OP50": 49,
#     "T_H_OP500": 50,
#     "T_H_OP510": 51,
#     "T_H_OP520": 52,
#     "T_H_OP530": 53,
#     "T_H_OP540": 54,
#     "T_H_OP55": 55,
#     "T_H_OP550": 56,
#     "T_H_OP80A": 57,
#     "T_H_OP80B": 58,
#     "T_H_OP90A": 59,
#     "T_H_OP90B": 60
# }

# # -------------------------
# # Queries
# # -------------------------

# update_query = f"""
# UPDATE {SCHEMA_NAME}.cycle_time_limits
# SET status = %s
# WHERE machine_id = %s
# """

# history_check_query = f"""
# SELECT status
# FROM {SCHEMA_NAME}.disconnection_history
# WHERE machine_id = %s
# ORDER BY time DESC
# LIMIT 1
# """

# history_insert_query = f"""
# INSERT INTO {SCHEMA_NAME}.disconnection_history
# (machine_id, status, time)
# VALUES (%s, %s, NOW())
# """

# try:

#     while True:

#         print("\n========================================")
#         print("Checking MongoDB DISCONNECT status...")
#         print("========================================")

#         updated_count = 0

#         cursor = collection.find(
#             {
#                 "L1Name": {"$in": list(machine_map.keys())},
#                 "signalname": "DISCONNECT"
#             },
#             {
#                 "_id": 0,
#                 "L1Name": 1,
#                 "value": 1
#             }
#         )

#         for doc in cursor:

#             machine_name = doc["L1Name"]
#             machine_id = machine_map[machine_name]
#             value = doc["value"]

#             status = (
#                 "DISCONNECTED"
#                 if value is True
#                 else "NOT_DISCONNECTED"
#             )

#             # -------------------------
#             # Update cycle_time_limits
#             # -------------------------

#             pg_cursor.execute(
#                 update_query,
#                 (status, machine_id)
#             )

#             # -------------------------
#             # History Logic
#             # -------------------------

#             pg_cursor.execute(
#                 history_check_query,
#                 (machine_id,)
#             )

#             last_record = pg_cursor.fetchone()

#             # First record for machine
#             if last_record is None:

#                 pg_cursor.execute(
#                     history_insert_query,
#                     (machine_id, status)
#                 )

#                 print(
#                     f"[HISTORY] First Status Logged "
#                     f"Machine={machine_id} "
#                     f"Status={status}"
#                 )

#             # Status changed
#             elif last_record[0] != status:

#                 previous_status = last_record[0]

#                 pg_cursor.execute(
#                     history_insert_query,
#                     (machine_id, status)
#                 )

#                 print(
#                     f"[HISTORY] Status Changed "
#                     f"Machine={machine_id} "
#                     f"{previous_status} -> {status}"
#                 )

#             if pg_cursor.rowcount > 0:

#                 updated_count += 1

#                 print(
#                     f"Updated Machine: {machine_name} "
#                     f"(ID={machine_id}) "
#                     f"Status={status}"
#                 )

#             else:

#                 print(
#                     f"Machine ID {machine_id} not found in cycle_time_limits"
#                 )

#         pg_conn.commit()

#         print(
#             f"\nCycle Completed Successfully "
#             f"({updated_count} machines updated)"
#         )

#         # Wait 5 seconds before next cycle
#         time.sleep(5)

# except KeyboardInterrupt:

#     print("\nStopping disconnect monitoring...")

# except Exception as e:

#     print(f"\nError: {e}")
#     pg_conn.rollback()

# finally:

#     pg_cursor.close()
#     pg_conn.close()
#     mongo_client.close()

#     print("Connections closed.")









#to save for history table === disconnection_history1




# from pymongo import MongoClient
# import psycopg2
# import time
# from datetime import datetime, timezone

# # -------------------------
# # MongoDB Connection
# # -------------------------
# mongo_client = MongoClient("mongodb://localhost:27017")

# mongo_db = mongo_client["MtLinki"]
# collection = mongo_db["L1Signal_Pool_Active"]

# # -------------------------
# # PostgreSQL Connection
# # -------------------------
# DATABASE_URL = "postgresql://postgres:1234@172.18.100.87:5432/Toyota_Demo"
# SCHEMA_NAME = "tiei_sample_5"

# pg_conn = psycopg2.connect(DATABASE_URL)
# pg_cursor = pg_conn.cursor()

# # -------------------------
# # Machine Mapping
# # -------------------------
# machine_map = {
#     "T_B_OP160": 2,
#     "T_B_OP180": 3,
#     "T_B_OP195A": 4,
#     "T_B_OP195B": 5,
#     "T_B_OP230": 6,
#     "T_B_OP235": 7,
#     "T_B_OP540": 8,
#     "T_C_OP10": 9,
#     "T_C_OP100": 10,
#     "T_C_OP160": 11,
#     "T_C_OP190": 12,
#     "T_C_OP30": 13,
#     "T_C_OP40": 14,
#     "T_C_OP90": 15,
#     "T_C_OP910": 16,
#     "T_C_OP911": 17,
#     "T_C_OP912": 18,
#     "T_C_OP913": 19,
#     "T_C_OP914": 20,
#     "T_C_OP915": 21,
#     "T_C_OP916": 22,
#     "T_H_OP10": 23,
#     "T_H_OP100A": 24,
#     "T_H_OP100B": 25,
#     "T_H_OP110A": 26,
#     "T_H_OP110B": 27,
#     "T_H_OP120A": 28,
#     "T_H_OP120B": 29,
#     "T_H_OP140A": 30,
#     "T_H_OP140B": 31,
#     "T_H_OP150A": 32,
#     "T_H_OP150B": 33,
#     "T_H_OP160A": 34,
#     "T_H_OP160B": 35,
#     "T_H_OP170A": 36,
#     "T_H_OP170B": 37,
#     "T_H_OP180A": 38,
#     "T_H_OP180B": 39,
#     "T_H_OP20": 40,
#     "T_H_OP230": 41,
#     "T_H_OP240": 42,
#     "T_H_OP250": 43,
#     "T_H_OP260": 44,
#     "T_H_OP270": 45,
#     "T_H_OP280": 46,
#     "T_H_OP285": 47,
#     "T_H_OP300": 48,
#     "T_H_OP50": 49,
#     "T_H_OP500": 50,
#     "T_H_OP510": 51,
#     "T_H_OP520": 52,
#     "T_H_OP530": 53,
#     "T_H_OP540": 54,
#     "T_H_OP55": 55,
#     "T_H_OP550": 56,
#     "T_H_OP80A": 57,
#     "T_H_OP80B": 58,
#     "T_H_OP90A": 59,
#     "T_H_OP90B": 60
# }

# # -------------------------
# # Existing update query (unchanged)
# # -------------------------
# update_query = f"""
# UPDATE {SCHEMA_NAME}.cycle_time_limits
# SET status = %s
# WHERE machine_id = %s
# """

# # -------------------------
# # Helper: Get latest disconnection_history1 row for a machine
# # -------------------------
# def get_latest_history_row(machine_id):
#     pg_cursor.execute(
#         f"""
#         SELECT status, start_time, stop_time
#         FROM {SCHEMA_NAME}.disconnection_history1
#         WHERE machine_id = %s
#         ORDER BY start_time DESC
#         LIMIT 1
#         """,
#         (machine_id,)
#     )
#     return pg_cursor.fetchone()  # Returns (status, start_time, stop_time) or None


# # -------------------------
# # Helper: Handle disconnection_history1 insert/update logic
# # -------------------------
# def handle_disconnection_history(machine_id, new_status):

#     latest_row = get_latest_history_row(machine_id)
#     now = datetime.now(timezone.utc)

#     # ── Case 1: No history row exists at all ──────────────────────────────────
#     # Only insert if machine is DISCONNECTED (ignore NOT_DISCONNECTED with no history)
#     if latest_row is None:
#         if new_status == "DISCONNECTED":
#             pg_cursor.execute(
#                 f"""
#                 INSERT INTO {SCHEMA_NAME}.disconnection_history1
#                     (machine_id, status, start_time, stop_time)
#                 VALUES (%s, %s, %s, NULL)
#                 """,
#                 (machine_id, "DISCONNECTED", now)
#             )
#             print(f"  [HISTORY] Machine {machine_id}: First DISCONNECTED event — row inserted (start_time={now})")
#         else:
#             # NOT_DISCONNECTED with no prior history → do nothing
#             pass
#         return

#     latest_status, latest_start, latest_stop = latest_row

#     # ── Case 2: Latest row is DISCONNECTED with no stop_time ─────────────────
#     if latest_status == "DISCONNECTED" and latest_stop is None:

#         if new_status == "DISCONNECTED":
#             # Still disconnected → do nothing
#             pass

#         elif new_status == "NOT_DISCONNECTED":
#             # Machine reconnected → fill stop_time on the open row
#             pg_cursor.execute(
#                 f"""
#                 UPDATE {SCHEMA_NAME}.disconnection_history1
#                 SET stop_time = %s
#                 WHERE machine_id = %s
#                   AND status = 'DISCONNECTED'
#                   AND stop_time IS NULL
#                 """,
#                 (now, machine_id)
#             )
#             print(f"  [HISTORY] Machine {machine_id}: Reconnected — stop_time={now} filled")

#     # ── Case 3: Latest row is DISCONNECTED and stop_time is already filled ────
#     # OR latest row is NOT_DISCONNECTED (though we never insert NOT_DISCONNECTED rows)
#     else:
#         if new_status == "DISCONNECTED":
#             # New disconnection event → insert fresh row
#             pg_cursor.execute(
#                 f"""
#                 INSERT INTO {SCHEMA_NAME}.disconnection_history1
#                     (machine_id, status, start_time, stop_time)
#                 VALUES (%s, %s, %s, NULL)
#                 """,
#                 (machine_id, "DISCONNECTED", now)
#             )
#             print(f"  [HISTORY] Machine {machine_id}: New DISCONNECTED event — row inserted (start_time={now})")

#         elif new_status == "NOT_DISCONNECTED":
#             # Already reconnected/closed → do nothing
#             pass


# # -------------------------
# # Main Loop
# # -------------------------
# try:

#     while True:

#         print("\n========================================")
#         print("Checking MongoDB DISCONNECT status...")
#         print("========================================")

#         updated_count = 0

#         cursor = collection.find(
#             {
#                 "L1Name": {"$in": list(machine_map.keys())},
#                 "signalname": "DISCONNECT"
#             },
#             {
#                 "_id": 0,
#                 "L1Name": 1,
#                 "value": 1
#             }
#         )

#         for doc in cursor:

#             machine_name = doc["L1Name"]
#             machine_id = machine_map[machine_name]
#             value = doc["value"]

#             status = (
#                 "DISCONNECTED"
#                 if value is True
#                 else "NOT_DISCONNECTED"
#             )

#             # ── Existing logic (unchanged) ────────────────────────────────────
#             pg_cursor.execute(
#                 update_query,
#                 (status, machine_id)
#             )

#             if pg_cursor.rowcount > 0:

#                 updated_count += pg_cursor.rowcount

#                 print(
#                     f"Updated Machine: {machine_name} "
#                     f"(ID={machine_id}) "
#                     f"Status={status}"
#                 )

#             else:

#                 print(
#                     f"Machine ID {machine_id} not found in cycle_time_limits"
#                 )

#             # ── New disconnection history logic ───────────────────────────────
#             handle_disconnection_history(machine_id, status)

#         pg_conn.commit()

#         print(
#             f"\nCycle Completed Successfully "
#             f"({updated_count} machines updated)"
#         )

#         time.sleep(5)

# except KeyboardInterrupt:

#     print("\nStopping disconnect monitoring...")

# except Exception as e:

#     print(f"\nError: {e}")
#     pg_conn.rollback()

# finally:

#     pg_cursor.close()
#     pg_conn.close()
#     mongo_client.close()

#     print("Connections closed.")










# import time

# from database import (
#     collection,
#     pg_conn,
#     pg_cursor,
#     mongo_client
# )

# from config import (
#     machine_map,
#     SCHEMA_NAME
# )

# from utils import (
#     handle_disconnection_history
# )

# update_query = f"""
# UPDATE {SCHEMA_NAME}.cycle_time_limits
# SET status = %s
# WHERE machine_id = %s
# """

# try:

#     while True:

#         print("\n========================================")
#         print("Checking MongoDB DISCONNECT status...")
#         print("========================================")

#         updated_count = 0

#         cursor = collection.find(
#             {
#                 "L1Name": {"$in": list(machine_map.keys())},
#                 "signalname": "DISCONNECT"
#             },
#             {
#                 "_id": 0,
#                 "L1Name": 1,
#                 "value": 1
#             }
#         )

#         for doc in cursor:

#             machine_name = doc["L1Name"]

#             machine_id = machine_map[machine_name]

#             value = doc["value"]

#             status = (
#                 "DISCONNECTED"
#                 if value is True
#                 else "NOT_DISCONNECTED"
#             )

#             pg_cursor.execute(
#                 update_query,
#                 (status, machine_id)
#             )

#             if pg_cursor.rowcount > 0:

#                 updated_count += pg_cursor.rowcount

#                 print(
#                     f"Updated Machine: {machine_name} "
#                     f"(ID={machine_id}) "
#                     f"Status={status}"
#                 )

#             else:

#                 print(
#                     f"Machine ID {machine_id} "
#                     f"not found in cycle_time_limits"
#                 )

#             handle_disconnection_history(
#                 machine_id,
#                 status
#             )

#         pg_conn.commit()

#         print(
#             f"\nCycle Completed Successfully "
#             f"({updated_count} machines updated)"
#         )

#         time.sleep(5)

# except KeyboardInterrupt:

#     print("\nStopping disconnect monitoring...")

# except Exception as e:

#     print(f"\nError: {e}")

#     pg_conn.rollback()

# finally:

#     pg_cursor.close()

#     pg_conn.close()

#     mongo_client.close()

#     print("Connections closed.")



import time
from datetime import datetime

from pony.orm import db_session

from database import (
    collection,
    pg_conn,
    mongo_client,
    init_disconnect_tables
)

from config import (
    machine_map
)

from utils import (
    handle_disconnection_history
)

from models import (
    CycleTimeLimits
)


@db_session
def update_machine_status(machine_id, status):

    row = CycleTimeLimits.get(
        machine_id=machine_id
    )

    if row:

        row.status = status

        return True

    return False


init_disconnect_tables()

try:

    while True:

        print("\n========================================")
        print("Checking MongoDB DISCONNECT status...")
        print("========================================")

        updated_count = 0
        skipped_count = 0
        cycle_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor = collection.find(
            {
                "L1Name": {"$in": list(machine_map.keys())},
                "signalname": "DISCONNECT"
            },
            {
                "_id": 0,
                "L1Name": 1,
                "value": 1
            }
        )

        for doc in cursor:

            machine_name = doc["L1Name"]

            machine_id = machine_map[machine_name]

            value = doc["value"]

            status = (
                "DISCONNECTED"
                if value is True
                else "NOT_DISCONNECTED"
            )

            updated = update_machine_status(
                machine_id,
                status
            )

            if updated:

                updated_count += 1

                print(
                    f"  [{cycle_time}] ✅ UPDATED  | Machine: {machine_name} "
                    f"(ID={machine_id}) | Status: {status}"
                )

            else:

                skipped_count += 1

                print(
                    f"  [{cycle_time}] ⚠️ SKIPPED  | Machine ID {machine_id} "
                    f"not found in cycle_time_limits"
                )

            # Still uses raw SQL because disconnection_history1
            # is a TimescaleDB hypertable
            handle_disconnection_history(
                machine_id,
                status
            )

        # Needed because handle_disconnection_history()
        # still uses psycopg2 raw SQL
        pg_conn.commit()

        print(
            f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
            f"Cycle complete — ✅ {updated_count} updated, "
            f"⚠️ {skipped_count} skipped."
        )

        time.sleep(5)

except KeyboardInterrupt:

    print("\nStopping disconnect monitoring...")

except Exception as e:

    print(f"\nError: {e}")

    pg_conn.rollback()

finally:

    pg_conn.close()

    mongo_client.close()

    print("Connections closed.")