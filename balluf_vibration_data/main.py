import sys
import argparse
import time
import math
import urllib3
from config import (
    INFLUXDB_1, INFLUXDB_2, INFLUXDB_3, INFLUXDB_4, POSTGRES,
    MACHINE_INFLUX_MAPPING, MACHINE_SQL_MCT_ID_MAPPING, MACHINE_CONFIG,
    PORT_INFLUX_MAPPING, PARAMETER_MAPPING
)
from database import InfluxDBManager, PostgreSQLManager
from models import VibrationDataPoint, MachineConfig, VibrationMachineLog
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict

# Suppress SSL warnings since we're using verify_ssl=False
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def process_mct_row(
    mct_row: dict,
    machine_name: str,
    influx_managers: dict,
    postgres_manager: PostgreSQLManager,
    machine_config_objects: dict
):
    """Process a single sql_server_mct_data row"""
    print()
    print("=" * 70)
    print(f"PROCESSING MCT ROW - Machine: {machine_name}")
    print("=" * 70)

    mct_time = mct_row.get("time")

    if not mct_time:
        print(f"✗ Skipping MCT row - missing time")
        return

    # Convert mct_time to datetime if it's a string
    if isinstance(mct_time, str):
        mct_time = datetime.fromisoformat(mct_time.replace('Z', '+00:00'))
    # Ensure mct_time is timezone-aware
    if mct_time.tzinfo is None:
        mct_time = mct_time.replace(tzinfo=timezone.utc)

    print(f"MCT Row Time: {mct_time}")

    # Extract cycle_time from MCT row
    cycle_time = mct_row.get('cycle_time')
    if cycle_time is None:
        print(f"✗ Skipping {machine_name} - cycle_time not found in MCT row")
        return
    # Convert cycle_time to integer (handle string or float)
    try:
        cycle_time = int(cycle_time)
    except (ValueError, TypeError):
        print(f"✗ Skipping {machine_name} - invalid cycle_time value: {cycle_time}")
        return
    print(f"Cycle Time: {cycle_time} seconds")

    # Get machine_id from PostgreSQL
    machine_id = postgres_manager.get_machine_id(machine_name)
    if not machine_id:
        print(f"✗ Skipping {machine_name} - machine_id not found in database.")
        return

    # Get the InfluxDB instance for this machine
    influx_instance = MACHINE_INFLUX_MAPPING.get(machine_name, 1)
    influx_manager = influx_managers[influx_instance]

    # Get machine configuration
    machine_config = MACHINE_CONFIG.get(machine_name)
    if not machine_config:
        print(f"✗ Skipping {machine_name} - no configuration found.")
        return

    # Connect to InfluxDB if not already connected (with error handling)
    if influx_manager.client is None:
        try:
            influx_manager.connect()
        except Exception as e:
            print(f"✗ InfluxDB connection failed: {e}")
            print(f"⚠ Row processing skipped")
            print("=" * 70)
            return

    # Get SQL MCT machine_id for fetching next rows
    sql_machine_id = MACHINE_SQL_MCT_ID_MAPPING.get(machine_name)

    # Try to find a row with InfluxDB data
    found_row_with_data = try_find_row_with_influx_data(
        influx_manager,
        postgres_manager,
        machine_name,
        machine_id,
        sql_machine_id,
        mct_row,
        cycle_time,
        machine_config
    )

    if found_row_with_data:
        print("=" * 70)
    else:
        print(f"✗ No InfluxDB data found for current row or next 5 rows")
        print("=" * 70)


def try_find_row_with_influx_data(
    influx_manager: InfluxDBManager,
    postgres_manager: PostgreSQLManager,
    machine_name: str,
    machine_id: int,
    sql_machine_id: int,
    initial_mct_row: dict,
    initial_cycle_time: int,
    machine_config: dict
) -> bool:
    """Try to find a row with InfluxDB data, checking current row and next 5 rows"""
    # If no data for initial row, fetch next 5 rows
    initial_time = initial_mct_row.get("time")
    if isinstance(initial_time, str):
        initial_time = datetime.fromisoformat(initial_time.replace('Z', '+00:00'))
    if initial_time.tzinfo is None:
        initial_time = initial_time.replace(tzinfo=timezone.utc)

    print(f"Checking for InfluxDB data...")

    # Check initial row for data
    has_data = check_and_process_row(
        influx_manager,
        postgres_manager,
        machine_name,
        machine_id,
        initial_mct_row,
        initial_cycle_time,
        machine_config,
        is_initial_check=True
    )

    if has_data:
        # Initial row had data, it was already logged and processed
        return True

    # No data for initial row, fetch next 5 rows
    print(f"No data for initial row, checking next 5 rows...")

    next_rows = postgres_manager.fetch_next_sql_server_mct_rows(sql_machine_id, initial_time, limit=5)

    if not next_rows:
        print(f"  - No next rows found")
        return False

    print(f"  - Found {len(next_rows)} next rows to check")

    last_row_checked = None
    last_row_time = None
    last_row_cycle_time = None

    for idx, row in enumerate(next_rows, 1):
        row_time = row.get("time")
        row_cycle_time = row.get('cycle_time')

        if not row_time or not row_cycle_time:
            print(f"  - Row {idx}: Missing time or cycle_time, skipping")
            continue

        # Convert row_time to datetime if it's a string
        if isinstance(row_time, str):
            row_time = datetime.fromisoformat(row_time.replace('Z', '+00:00'))
        if row_time.tzinfo is None:
            row_time = row_time.replace(tzinfo=timezone.utc)

        # Convert cycle_time to integer
        try:
            row_cycle_time = int(row_cycle_time)
        except (ValueError, TypeError):
            print(f"  - Row {idx}: Invalid cycle_time, skipping")
            continue

        print(f"  - Checking row {idx}: {row_time}")

        has_data = check_and_process_row(
            influx_manager,
            postgres_manager,
            machine_name,
            machine_id,
            row,
            row_cycle_time,
            machine_config,
            is_initial_check=False
        )

        if has_data:
            print(f"  ✓ Found data for row {idx}, processing it")
            return True

        # Store the last row checked
        last_row_checked = row
        last_row_time = row_time
        last_row_cycle_time = row_cycle_time

    # If none of the 5 rows had data, log watermark to vibration_machine_logs
    if last_row_checked:
        print(f"  ✗ No InfluxDB data found for any of the 5 rows")
        print(f"  - Logging watermark to vibration_machine_logs for {last_row_time}")
        program_file_id = postgres_manager.insert_vibration_machine_log(machine_id, last_row_time, cycle_time=last_row_cycle_time)
        print(f"  ✓ Logged watermark to vibration_machine_logs - ID: {program_file_id}, Time: {last_row_time}")
        return True

    return False


def check_and_process_row(
    influx_manager: InfluxDBManager,
    postgres_manager: PostgreSQLManager,
    machine_name: str,
    machine_id: int,
    mct_row: dict,
    cycle_time: int,
    machine_config: dict,
    is_initial_check: bool
) -> bool:
    """Check if InfluxDB has data for a row and process it if found"""
    mct_time = mct_row.get("time")
    if isinstance(mct_time, str):
        mct_time = datetime.fromisoformat(mct_time.replace('Z', '+00:00'))
    if mct_time.tzinfo is None:
        mct_time = mct_time.replace(tzinfo=timezone.utc)

    # Get port names
    port1_name = machine_config["port1"]
    port1_influx = PORT_INFLUX_MAPPING.get(port1_name, port1_name)
    port2_name = machine_config["port2"]
    port2_influx = PORT_INFLUX_MAPPING.get(port2_name, port2_name)

    # Check if port1 or port2 has data
    port1_data = influx_manager.fetch_port_data(port1_influx, mct_time.isoformat(), duration_seconds=cycle_time)
    port2_data = influx_manager.fetch_port_data(port2_influx, mct_time.isoformat(), duration_seconds=cycle_time)

    has_data = (port1_data is not None and len(port1_data) > 0) or (port2_data is not None and len(port2_data) > 0)

    if has_data:
        if not is_initial_check:
            print(f"  ✓ Found InfluxDB data for this row")

        # Process port1 if it has data
        if port1_data and len(port1_data) > 0:
            print(f"Processing Port 1: {port1_name} (InfluxDB: {port1_influx})")
            print(f"  - Duration: {cycle_time} seconds ({len(port1_data)} points)")
            try:
                process_machine_ports(
                    influx_manager,
                    postgres_manager,
                    machine_name,
                    machine_id,
                    port1_name,
                    port1_influx,
                    mct_time,
                    cycle_time,
                    points=port1_data
                )
            except Exception as e:
                print(f"✗ Error processing {port1_name}: {e}")

        # Process port2 if it has data
        if port2_data and len(port2_data) > 0:
            print(f"Processing Port 2: {port2_name} (InfluxDB: {port2_influx})")
            print(f"  - Duration: {cycle_time} seconds ({len(port2_data)} points)")
            try:
                process_machine_ports(
                    influx_manager,
                    postgres_manager,
                    machine_name,
                    machine_id,
                    port2_name,
                    port2_influx,
                    mct_time,
                    cycle_time,
                    points=port2_data
                )
            except Exception as e:
                print(f"✗ Error processing {port2_name}: {e}")

        return True
    else:
        if is_initial_check:
            print(f"  ✗ No InfluxDB data for initial row")
        else:
            print(f"  ✗ No InfluxDB data for this row")
        return False


def compute_cycle_rms(data_points: List[VibrationDataPoint]) -> Dict[str, Optional[float]]:
    """Compute Root Mean Square (RMS) value over cycle duration for all 7 parameters:
    RMS = sqrt( (1 / N) * sum(x_i^2) )
    """
    fields = [
        'contact_temperature',
        'v_peak_x',
        'v_peak_y',
        'v_peak_z',
        'v_rms_x',
        'v_rms_y',
        'v_rms_z'
    ]
    rms_values: Dict[str, Optional[float]] = {}
    for field in fields:
        valid_vals = [getattr(p, field) for p in data_points if getattr(p, field) is not None]
        if valid_vals:
            sum_sq = sum(v * v for v in valid_vals)
            rms_values[field] = math.sqrt(sum_sq / len(valid_vals))
        else:
            rms_values[field] = None
    return rms_values


def process_machine_ports(
    influx_manager: InfluxDBManager,
    postgres_manager: PostgreSQLManager,
    machine_name: str,
    machine_id: int,
    port_name: str,  # Human-readable name for database storage
    influx_port_name: str,  # Actual InfluxDB measurement name for query
    signal_time: datetime,
    cycle_time: int,  # Duration in seconds from MCT row
    points: Optional[List[dict]] = None
):
    """Fetch vibration data from InfluxDB for a specific port, compute cycle RMS, and insert into PostgreSQL"""
    if points is None:
        points = influx_manager.fetch_port_data(influx_port_name, signal_time.isoformat(), duration_seconds=cycle_time)

    if not points:
        print(f"  ✗ No data found in InfluxDB for port {influx_port_name}")
        print(f"  ⚠ Skipping vibration_data insertion")
        return

    print(f"  ✓ Found {len(points)} records in InfluxDB (duration: {cycle_time} seconds)")

    # Convert to VibrationDataPoint objects using human-readable port name
    data_points = [
        VibrationDataPoint.from_influx_point(machine_id, port_name, point)
        for point in points
    ]

    # Compute cycle RMS for all 7 parameters over the full duration
    rms_values = compute_cycle_rms(data_points)
    print(f"  ✓ Computed cycle RMS for {port_name} (over {len(data_points)} points):")
    for param_name, val in rms_values.items():
        if val is not None:
            print(f"      • {param_name}: {val:.4f}")

    # Insert cycle log into vibration_machine_logs
    program_file_id = postgres_manager.insert_vibration_machine_log(
        machine_id=machine_id,
        program_file_time=signal_time,
        port=port_name,
        contact_temperature=rms_values.get('contact_temperature'),
        v_peak_x=rms_values.get('v_peak_x'),
        v_peak_y=rms_values.get('v_peak_y'),
        v_peak_z=rms_values.get('v_peak_z'),
        v_rms_x=rms_values.get('v_rms_x'),
        v_rms_y=rms_values.get('v_rms_y'),
        v_rms_z=rms_values.get('v_rms_z'),
        cycle_time=cycle_time
    )
    print(f"  ✓ Logged to vibration_machine_logs - ID: {program_file_id}, Port: {port_name}, Time: {signal_time}")

    # Set program_file_id on data points
    for dp in data_points:
        dp.program_file_id = program_file_id

    # Insert into PostgreSQL vibration_data table
    inserted_count = postgres_manager.insert_vibration_data(data_points)
    print(f"  ✓ Inserted {inserted_count} records into vibration_data table")

    # Perform abnormality detection and corrective activity tracking based on cycle RMS values
    detect_abnormalities(
        postgres_manager,
        machine_name,
        machine_id,
        port_name,
        rms_values,
        signal_time
    )


def detect_abnormalities(
    postgres_manager: PostgreSQLManager,
    machine_name: str,
    machine_id: int,
    port_name: str,
    rms_values: Dict[str, Optional[float]],
    signal_time: datetime
):
    """Detect abnormalities in vibration data based on cycle RMS values and update corrective activity table"""
    try:
        print(f"  - Checking for abnormalities based on cycle RMS values...")

        # Get parameter mapping for this machine and port from config
        if machine_name not in PARAMETER_MAPPING:
            print(f"  - No parameter mapping for machine {machine_name}")
            return

        if port_name not in PARAMETER_MAPPING[machine_name]:
            print(f"  - No parameter mapping for port {port_name} on machine {machine_name}")
            return

        param_map = PARAMETER_MAPPING[machine_name][port_name]
        print(f"  - Found {len(param_map)} parameters to check")

        abnormalities_found = 0

        # Check each parameter's cycle RMS value against limits
        for param_name, rms_value in rms_values.items():
            if param_name not in param_map or rms_value is None:
                continue

            # Get both IDs from static mapping
            param_ids = param_map[param_name]
            corrective_id = param_ids['corrective_id']  # For corrective_activity table
            vibration_table_id = param_ids['vibration_table_id']  # For fetching limits

            # Fetch warning and critical limits from vibration_parameters table using vibration_table_id
            param_limits = postgres_manager.fetch_parameter_limits(vibration_table_id)
            if not param_limits:
                print(f"    - No limits found for vibration_table_id {vibration_table_id}, skipping")
                continue

            warning_limit = param_limits['warning_limit']
            critical_limit = param_limits['critical_limit']

            # Determine condition based on cycle RMS value
            condition_id = 1  # OK
            if rms_value >= critical_limit:
                condition_id = 3  # Critical
            elif rms_value >= warning_limit:
                condition_id = 2  # Warning

            # Only process if abnormal (condition > 1)
            if condition_id > 1:
                abnormalities_found += 1

                # Check if this (corrective_id, condition_id) combination already exists
                existing_activity = postgres_manager.check_corrective_activity_exists(corrective_id, condition_id)

                if existing_activity:
                    # Update existing record
                    activity_id = existing_activity['id']
                    postgres_manager.update_corrective_activity(activity_id, rms_value, signal_time)
                    print(f"    - Updated corrective activity: corrective_id={corrective_id}, condition={condition_id}, rms_value={rms_value:.4f}")
                else:
                    # Insert new record
                    postgres_manager.insert_corrective_activity(corrective_id, condition_id, rms_value, signal_time)
                    print(f"    - New corrective activity: corrective_id={corrective_id}, condition={condition_id}, rms_value={rms_value:.4f}")

        if abnormalities_found == 0:
            print(f"  - No abnormalities detected (all parameters within limits)")
        else:
            print(f"  - Total abnormalities processed: {abnormalities_found}")
    except Exception as e:
        print(f"  ✗ Error during abnormality detection: {e}")
        postgres_manager.rollback()



def main():
    """Main function to orchestrate data transfer from InfluxDB to PostgreSQL using sql_server_mct_data"""
    parser = argparse.ArgumentParser(description='Process vibration data from InfluxDB based on sql_server_mct_data')
    parser.add_argument('--start-date', type=str, help='Start date for processing (ISO format: YYYY-MM-DD)')
    args = parser.parse_args()

    print()
    print("=" * 70)
    print("BALLUFF INFLUXDB -> POSTGRESQL (SQL Server MCT Data)")
    print("=" * 70)
    print()

    # Parse start date if provided
    start_date = None
    if args.start_date:
        try:
            start_date = datetime.fromisoformat(args.start_date)
            print(f"Processing from start date: {start_date}")
        except ValueError:
            print(f"Invalid start date format: {args.start_date}")
            print("Please use ISO format: YYYY-MM-DD")
            sys.exit(1)

    # Initialize InfluxDB managers for all instances
    influx_managers = {
        1: InfluxDBManager(INFLUXDB_1),
        2: InfluxDBManager(INFLUXDB_2),
        3: InfluxDBManager(INFLUXDB_3),
        4: InfluxDBManager(INFLUXDB_4),
    }

    # Initialize PostgreSQL manager
    postgres_manager = PostgreSQLManager(POSTGRES)

    try:
        # Connect to PostgreSQL
        postgres_manager.connect()

        # Create vibration_machines table and initialize machines
        postgres_manager.create_vibration_machines_table()

        # Convert MACHINE_CONFIG dict to MachineConfig objects
        machine_config_objects = {}
        for idx, (machine_name, config) in enumerate(MACHINE_CONFIG.items(), start=1):
            machine_config_objects[machine_name] = MachineConfig(
                machine_id=idx,
                machine_name=config["machine_name"],
                machine_location=config["machine_location"],
                port1=config["port1"],
                port2=config["port2"]
            )

        postgres_manager.initialize_machines(machine_config_objects)

        # Create vibration_machine_logs table
        postgres_manager.create_vibration_machine_logs_table()

        # Create vibration_data hypertable
        postgres_manager.create_vibration_data_hypertable()

        # Get configured machine names
        machine_names = list(MACHINE_CONFIG.keys())
        print(f"Configured machines: {machine_names}")

        # Initial processing - fetch first row matching start date from sql_server_mct_data
        if start_date:
            print()
            print("=" * 70)
            print("INITIAL PROCESSING PHASE")
            print("=" * 70)
            print(f"Fetching initial rows from sql_server_mct_data from {start_date}...")

            any_rows_found = False
            for machine_name in machine_names:
                sql_machine_id = MACHINE_SQL_MCT_ID_MAPPING.get(machine_name)
                if not sql_machine_id:
                    print(f"WARNING: No SQL MCT ID mapping for {machine_name}")
                    continue

                print()
                print(f"Processing machine: {machine_name} (SQL MCT ID: {sql_machine_id})")
                mct_rows = postgres_manager.fetch_sql_server_mct_data(sql_machine_id, start_date)

                if mct_rows:
                    any_rows_found = True
                    # Process the first row
                    first_row = mct_rows[0]
                    print(f"✓ Found {len(mct_rows)} rows. Processing first row with time: {first_row['time']}")
                    process_mct_row(first_row, machine_name, influx_managers, postgres_manager, machine_config_objects)
                else:
                    print(f"✗ No rows found for {machine_name} in sql_server_mct_data")

            if not any_rows_found:
                print()
                print("=" * 70)
                print(f"NO ROWS FOUND >= {start_date} FOR ANY MACHINE - SKIPPING INITIAL PROCESSING")
                print("Will wait for rows to appear in sql_server_mct_data...")
        else:
            # No start date provided - check last processed time and monitor from there
            print()
            print("=" * 70)
            print("NO START DATE PROVIDED - CHECKING LAST PROCESSED TIME")
            print("=" * 70)
            latest_time = postgres_manager.get_latest_program_file_time()
            if latest_time:
                print(f"✓ Last processed time found: {latest_time}")
                print(f"Will monitor for new rows after this time...")
            else:
                print(f"✗ No previous processed time found")
                print(f"Will check for initial data from 2026-10-04 in monitoring loop...")

        # Continuous monitoring - check every 60 seconds, process rows every 2 hours
        print("\n" + "=" * 70)
        print("Starting continuous monitoring (checking every 60 seconds, processing every 2 hours)...")
        print("=" * 70)

        while True:
            try:
                # Check if there's a row >= 2hrs from last processed time
                rows_processed_this_cycle = False

                for machine_name in machine_names:
                    # Get machine_id from PostgreSQL
                    machine_id = postgres_manager.get_machine_id(machine_name)
                    if not machine_id:
                        continue

                    # Get the latest processed time for this specific machine
                    latest_time = postgres_manager.get_latest_program_file_time(machine_id)

                    # If no logs for this machine, start from 2026-10-04
                    if not latest_time:
                        latest_time = datetime(2026, 10, 4, tzinfo=timezone.utc)
                        print(f"  No previous logs for {machine_name}, starting from {latest_time}")

                    # Calculate the time threshold (2 hours after last processed time)
                    time_threshold = latest_time + timedelta(hours=2)
                    current_time = datetime.now(timezone.utc)

                    print()
                    print(f"Checking for new data for {machine_name}...")
                    print(f"  Last processed: {latest_time}")
                    print(f"  2-hour threshold: {time_threshold}")

                    sql_machine_id = MACHINE_SQL_MCT_ID_MAPPING.get(machine_name)
                    if not sql_machine_id:
                        continue

                    # Fetch rows after last processed time
                    new_rows = postgres_manager.fetch_new_sql_server_mct_data(sql_machine_id, latest_time)

                    if new_rows:
                        print(f"  Found {len(new_rows)} rows in sql_server_mct_data for {machine_name}")
                        # Check if any row meets the 8-hour threshold
                        for row in new_rows:
                            row_time = row['time']
                            if isinstance(row_time, str):
                                row_time = datetime.fromisoformat(row_time.replace('Z', '+00:00'))
                            # Ensure row_time is timezone-aware
                            if row_time.tzinfo is None:
                                row_time = row_time.replace(tzinfo=timezone.utc)

                            if row_time >= time_threshold:
                                print()
                                print(f"Found row meeting 2-hour threshold for {machine_name}")
                                print(f"Row time: {row_time} (Threshold: {time_threshold})")
                                process_mct_row(row, machine_name, influx_managers, postgres_manager, machine_config_objects)
                                rows_processed_this_cycle = True
                                break  # Only process one row per machine per cycle
                            else:
                                print(f"  Row time: {row_time} (before 2-hour threshold)")
                    else:
                        print(f"  No new rows in sql_server_mct_data for {machine_name}")

                if not rows_processed_this_cycle:
                    print("  No rows to process this cycle")

                # Wait before next check (60 seconds)
                time.sleep(60)  # 60 seconds

            except KeyboardInterrupt:
                print("\nStopping continuous monitoring...")
                break
            except Exception as e:
                print(f"\n✗ Error in monitoring loop: {e}")
                import traceback
                traceback.print_exc()
                print("Continuing monitoring...")
                time.sleep(60)  # Wait 60 seconds before retry on error

        print()
        print("=" * 70)
        print("Monitoring stopped.")
        print("=" * 70)

    except Exception as e:
        print()
        print("=" * 70)
        print("ERROR")
        print("=" * 70)
        print(e)
        import traceback
        traceback.print_exc()
        postgres_manager.rollback()

    finally:
        # Close all InfluxDB connections
        for manager in influx_managers.values():
            manager.close()

        # Close PostgreSQL connection
        postgres_manager.close()


if __name__ == "__main__":
    main()
