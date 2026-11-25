










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
    machine_map_1
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
                "L1Name": {"$in": list(machine_map_1.keys())},
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

            machine_id = machine_map_1[machine_name]

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