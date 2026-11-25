#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Pressure Data Collector for Shared Folder Monitoring
======================================================

Module for monitoring pressure data CSV files from shared folders on Linux servers
Supports both local and shared folder monitoring with mount/unmount functionality

Usage:
    python air_pressure_data_shared.py --os linux --machine_id 1 --ip_address "//10.82.126.26/2nd-rough" --mount_location "/mnt/pressure_data/2nd-rough" --local_directory "G:\\GOKUL\\TOYOTA\\Collector_1\\2st-Rough"
    
    python air_pressure_data_shared.py --os windows --machine_id 1 --local_directory "G:\\GOKUL\\TOYOTA\\Collector_1\\2st-Rough"
"""

import os
import time
import shutil
import argparse
import subprocess
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta

from pony.orm import db_session, commit, desc

import database
from database import pg_conn, pg_cursor

from models import (
    PressureMonitoringMachine,
    PressureLogFile
)


# ==========================================================
# CONFIGURATION
# ==========================================================

POLL_INTERVAL = 5

LATEST_ROOT = r"G:\GOKUL\TOYOTA\Collector_1\latest"

MACHINES = [

    {
        "machine_id": 1,
        "machine_name": "2nd Rough",
        "watch_folder": r"G:\GOKUL\TOYOTA\Collector_1\2st-Rough",
        "pressure_column": "DM11001",
        "ip_address": "//10.82.126.26/2nd-rough",
        "mount_location": "/mnt/pressure_data/2nd-rough",
        "file_prefix": "025_324_JP0160101200001_B1519002RHM_log000_2STR_B.H."
    },

    {
        "machine_id": 2,
        "machine_name": "4th Finish",
        "watch_folder": r"G:\GOKUL\TOYOTA\Collector_1\4st-Finish",
        "pressure_column": "DM11006",
        "ip_address": "//10.82.126.26/4th-finish",
        "mount_location": "/mnt/pressure_data/4th-finish",
        "file_prefix": "025_324_JP0160101200001_B1519004RHM_log002_4STR_B.H."
    }

]


# ==========================================================
# ARGUMENT PARSING
# ==========================================================

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Pressure Data Collector for Shared Folder Monitoring')
    
    parser.add_argument('--os', type=str, choices=['linux', 'windows'], default='windows',
                        help='Operating system (linux/windows)')
    parser.add_argument('--machine_id', type=int, help='Machine ID to monitor (1 or 2)')
    parser.add_argument('--ip_address', type=str, help='Shared folder IP address (e.g., //10.82.126.26/2nd-rough)')
    parser.add_argument('--mount_location', type=str, help='Mount location on Linux (e.g., /mnt/pressure_data/2nd-rough)')
    parser.add_argument('--local_directory', type=str, help='Local directory path for Windows mode')
    parser.add_argument('--skip_mount', action='store_true', help='Skip mount operations (for Docker mode)')
    
    return parser.parse_args()


# ==========================================================
# PATH HELPERS
# ==========================================================

def get_machine_latest_folder(machine):

    folder = os.path.join(
        LATEST_ROOT,
        f"machine_{machine['machine_id']}"
    )

    os.makedirs(folder, exist_ok=True)

    return folder


def get_last_processed_file(machine):

    return os.path.join(
        get_machine_latest_folder(machine),
        "last_processed.txt"
    )


# ==========================================================
# MOUNT/UNMOUNT OPERATIONS (Linux)
# ==========================================================

def check_for_mount_drive(directory, ip_address=None, mount_location=None):
    """
    Check if shared drive is mounted
    For Linux: Check if mount point exists and is accessible
    """
    if os.name != 'posix':
        return True  # Windows doesn't need mount check
    
    try:
        # Check if mount location exists and is accessible
        if mount_location and os.path.exists(mount_location):
            # Try to list directory to verify it's mounted
            os.listdir(mount_location)
            return True
        return False
    except Exception as e:
        print(f"Mount check error: {e}")
        return False


def mount_shared_drive(ip_address, mount_location):
    """
    Mount shared drive on Linux using mount command
    """
    try:
        # Create mount directory if it doesn't exist
        os.makedirs(mount_location, exist_ok=True)
        
        # Mount command for SMB/CIFS share
        # Using credentials from environment or default
        mount_cmd = [
            'sudo', 'mount',
            '-t', 'cifs',
            ip_address,
            mount_location,
            '-o', 'username=guest,password=,rw,vers=3.0'
        ]
        
        print(f"Mounting {ip_address} to {mount_location}")
        result = subprocess.run(mount_cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"Successfully mounted {ip_address}")
            return True
        else:
            print(f"Mount failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"Mount error: {e}")
        return False


def unmount_drive(mount_location):
    """
    Unmount drive on Linux
    """
    try:
        if os.path.exists(mount_location):
            unmount_cmd = ['sudo', 'umount', mount_location]
            result = subprocess.run(unmount_cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"Successfully unmounted {mount_location}")
                return True
            else:
                print(f"Unmount failed: {result.stderr}")
                return False
        return True
    except Exception as e:
        print(f"Unmount error: {e}")
        return False


# ==========================================================
# LAST PROCESSED
# ==========================================================

@db_session
def get_last_processed(machine):
    try:
        from models import PressureLogFile
        machine_id = machine["machine_id"]
        
        # Get the latest row for the machine based on latest_time
        latest_log = PressureLogFile.select(lambda p: p.machine_id == machine_id and p.latest_time != None).order_by(desc(PressureLogFile.latest_time)).first()
        
        if latest_log:
            return latest_log.file_name, latest_log.latest_time
        return None, None
    except Exception as e:
        print(f"Error getting last processed from DB: {e}")
        return None, None


@db_session
def save_last_processed(machine, filename, file_time):
    try:
        from models import PressureLogFile
        machine_id = machine["machine_id"]
        
        log = PressureLogFile.get(machine_id=machine_id, file_name=filename)
        if log:
            log.latest_time = file_time
            commit()
            print(f"Successfully updated latest_time {file_time} for {filename} in database.")
        else:
            print(f"Failed to find log for {filename} to update latest_time.")
    except Exception as e:
        print(f"Error saving last processed to DB: {e}")


# ==========================================================
# FILE FUNCTIONS
# ==========================================================

def get_all_csv_files(machine):

    folder = machine["watch_folder"]

    expected_prefix = machine.get("file_prefix", "")

    files = [

        f

        for f in os.listdir(folder)

        if f.lower().endswith(".csv") and f.startswith(expected_prefix)

    ]

    if not files:

        return []

    # Return all files with their timestamps in IST format
    files_with_time = []
    for f in files:
        file_path = os.path.join(folder, f)
        file_time_epoch = os.path.getmtime(file_path)
        # Convert epoch to IST datetime
        file_time_ist = datetime.utcfromtimestamp(file_time_epoch) + timedelta(hours=5, minutes=30)
        files_with_time.append((f, file_time_ist))
    
    # Sort by timestamp
    files_with_time.sort(key=lambda x: x[1])
    
    return files_with_time


def get_new_files(machine, last_processed_time):

    all_files = get_all_csv_files(machine)
    
    if last_processed_time is None:
        # First run - process all files
        return all_files
    
    # Return only files newer than last processed time
    new_files = [(f, t) for f, t in all_files if t > last_processed_time]
    
    return new_files


def clear_latest_folder(machine):

    folder = get_machine_latest_folder(machine)

    for file in os.listdir(folder):

        if file.lower().endswith(".csv"):

            try:

                os.remove(
                    os.path.join(folder, file)
                )

            except Exception as e:

                print(
                    f"Delete Error : {e}"
                )


def copy_to_latest(machine, filename):

    source = os.path.join(
        machine["watch_folder"],
        filename
    )

    destination = os.path.join(
        get_machine_latest_folder(machine),
        filename
    )

    clear_latest_folder(machine)

    shutil.copy2(
        source,
        destination
    )

    return destination


# ==========================================================
# TIMESTAMP EXTRACTION
# ==========================================================

def extract_timestamp_from_filename(filename):
    """
    Extract timestamp from filename.
    Format: 025_324_JP0160101200001_B1519002RHM_log000_2STR_B.H.260619195927
    The timestamp is at the end: YYMMDDHHMMSS
    """
    try:
        # Remove file extension
        name_without_ext = filename.rsplit('.', 1)[0]
        
        # Get the last part (timestamp)
        # The timestamp is typically the last 12 digits before extension
        timestamp_str = name_without_ext[-12:]
        
        if len(timestamp_str) == 12 and timestamp_str.isdigit():
            # Parse YYMMDDHHMMSS format
            year = int("20" + timestamp_str[0:2])  # Add 20 for full year
            month = int(timestamp_str[2:4])
            day = int(timestamp_str[4:6])
            hour = int(timestamp_str[6:8])
            minute = int(timestamp_str[8:10])
            second = int(timestamp_str[10:12])
            
            from datetime import datetime
            return datetime(year, month, day, hour, minute, second)
        else:
            print(f"Could not extract timestamp from filename: {filename}")
            return None
            
    except Exception as e:
        print(f"Error extracting timestamp from {filename}: {e}")
        return None


# ==========================================================
# RMSE ABNORMALITY DETECTION AND CORRECTIVE ACTIVITY TRACKING
# ==========================================================

def get_rmse_parameter_limits(machine_id):
    """
    Get warning and critical limits for RMSE parameter from pressure_monitoring_machine table
    For machine_id 1: parameter_id 7007
    For machine_id 2: parameter_id 7008
    """
    try:
        # Query pressure_monitoring_machine table for warning and critical limits
        query = """
            SELECT warning_limit, critical_limit
            FROM tiei_sample_4.pressure_monitoring_machine
            WHERE id = %s
        """
        pg_cursor.execute(query, (machine_id,))
        result = pg_cursor.fetchone()
        
        if result:
            warning_limit, critical_limit = result
            print(f"RMSE Limits for machine {machine_id} from pressure_monitoring_machine: Warning={warning_limit}, Critical={critical_limit}")
            return warning_limit, critical_limit
        else:
            print(f"No limits found for machine_id {machine_id} in pressure_monitoring_machine")
            return None, None
            
    except Exception as e:
        print(f"Error getting RMSE parameter limits: {e}")
        return None, None


def calculate_rmse_condition(rmse_value, warning_limit, critical_limit):
    """
    Calculate condition based on RMSE value
    Returns:
        1 = OK
        2 = Warning
        3 = Critical
    """
    if rmse_value is None or warning_limit is None or critical_limit is None:
        return 1
    
    if rmse_value >= critical_limit:
        return 3  # Critical
    elif rmse_value >= warning_limit:
        return 2  # Warning
    else:
        return 1  # OK


def check_corrective_activity_exists(machine_parameters_id, parameter_condition_id):
    """
    Check if corrective activity record exists for (machine_parameters_id, parameter_condition_id) combination
    """
    try:
        query = """
            SELECT id, number_of_occurrences
            FROM tiei_sample_4.corrective_activity
            WHERE machine_parameters_id = %s AND parameter_condition_id = %s
        """
        pg_cursor.execute(query, (machine_parameters_id, parameter_condition_id))
        result = pg_cursor.fetchone()
        
        if result:
            return result[0], result[1]  # id, number_of_occurrences
        return None, None
        
    except Exception as e:
        print(f"Error checking corrective activity: {e}")
        return None, None


def insert_corrective_activity(machine_parameters_id, parameter_condition_id, recent_value, log_file_id):
    """
    Insert new corrective activity record
    """
    try:
        from datetime import datetime
        
        query = """
            INSERT INTO tiei_sample_4.corrective_activity
            (machine_parameters_id, date_of_identification, parameter_condition_id, recent_value, latest_occurrence, number_of_occurrences)
            VALUES (%s, %s, %s, %s, %s, 1)
        """
        pg_cursor.execute(query, (
            machine_parameters_id,
            datetime.now(),
            parameter_condition_id,
            recent_value,
            datetime.now()
        ))
        pg_conn.commit()
        print(f"Inserted new corrective activity: machine_parameters_id={machine_parameters_id}, parameter_condition_id={parameter_condition_id}, value={recent_value:.4f}")
        
    except Exception as e:
        pg_conn.rollback()
        print(f"Error inserting corrective activity: {e}")


def update_corrective_activity(activity_id, recent_value):
    """
    Update existing corrective activity record
    Increments number_of_occurrences and updates latest_occurrence and recent_value
    """
    try:
        from datetime import datetime
        
        query = """
            UPDATE tiei_sample_4.corrective_activity
            SET recent_value = %s,
                latest_occurrence = %s,
                number_of_occurrences = number_of_occurrences + 1
            WHERE id = %s
        """
        pg_cursor.execute(query, (recent_value, datetime.now(), activity_id))
        pg_conn.commit()
        print(f"Updated corrective activity: id={activity_id}, new value={recent_value:.4f}")
        
    except Exception as e:
        pg_conn.rollback()
        print(f"Error updating corrective activity: {e}")


def process_rmse_corrective_activity(machine_id, rmse_value, log_file_id):
    """
    Process RMSE-based corrective activity tracking
    """
    try:
        # Get RMSE parameter limits
        rmse_parameter_map = {
            1: 7007,  # 2nd Rough
            2: 7008   # 4th Finish
        }
        
        machine_parameters_id = rmse_parameter_map.get(machine_id)
        if not machine_parameters_id:
            print(f"No RMSE parameter configured for machine_id {machine_id}")
            return
        
        # Get warning and critical limits
        warning_limit, critical_limit = get_rmse_parameter_limits(machine_id)
        if warning_limit is None or critical_limit is None:
            print("Could not get RMSE limits, skipping corrective activity tracking")
            return
        
        # Calculate condition
        parameter_condition_id = calculate_rmse_condition(rmse_value, warning_limit, critical_limit)
        
        print(f"\nRMSE Abnormality Detection:")
        print(f"  RMSE Value: {rmse_value:.4f}")
        print(f"  Warning Limit: {warning_limit}")
        print(f"  Critical Limit: {critical_limit}")
        print(f"  Condition: {parameter_condition_id} ({'OK' if parameter_condition_id == 1 else 'WARNING' if parameter_condition_id == 2 else 'CRITICAL'})")
        
        # Only process if condition is warning or critical
        if parameter_condition_id > 1:
            # Check if corrective activity already exists
            activity_id, occurrences = check_corrective_activity_exists(machine_parameters_id, parameter_condition_id)
            
            if activity_id:
                # Update existing activity
                print(f"  Updating existing corrective activity (ID: {activity_id}, previous occurrences: {occurrences})")
                update_corrective_activity(activity_id, rmse_value)
            else:
                # Insert new activity
                print(f"  Creating new corrective activity")
                insert_corrective_activity(machine_parameters_id, parameter_condition_id, rmse_value, log_file_id)
        else:
            print(f"  RMSE is within normal limits, no corrective action needed")
            
    except Exception as e:
        print(f"Error processing RMSE corrective activity: {e}")


# ==========================================================
# STATISTICAL CALCULATIONS
# ==========================================================

def calculate_pressure_statistics(df):
    """
    Calculate statistical parameters from pressure data
    """
    try:
        pressure_values = df['pressure_value'].values
        
        # Mean Pressure - average of all pressure values
        mean_pressure = float(np.mean(pressure_values))
        
        # Peak Pressure - maximum pressure value
        peak_pressure = float(np.max(pressure_values))
        
        # Start Time - timestamp of first sample
        start_time = pd.to_datetime(df['timestamp'].iloc[0]).to_pydatetime()
        
        # End Time - timestamp of last sample
        end_time = pd.to_datetime(df['timestamp'].iloc[-1]).to_pydatetime()
        
        # Cycle Duration - difference between end and start time in seconds
        cycle_duration_seconds = (end_time - start_time).total_seconds()
        
        # Pressure Ripple - standard deviation of pressure readings
        pressure_ripple = float(np.std(pressure_values))
        
        return {
            'mean_pressure': mean_pressure,
            'peak_pressure': peak_pressure,
            'start_time': start_time,
            'end_time': end_time,
            'cycle_duration_seconds': cycle_duration_seconds,
            'pressure_ripple': pressure_ripple
        }
    except Exception as e:
        print(f"Error calculating pressure statistics: {e}")
        return None


def calculate_rmse(current_pressure, baseline_pressure):
    """
    Calculate RMSE between current and baseline pressure profiles
    """
    try:
        # Ensure both arrays are numpy arrays
        current = np.array(current_pressure)
        baseline = np.array(baseline_pressure)
        
        # Align profiles by truncating to the shorter length
        min_length = min(len(current), len(baseline))
        current_aligned = current[:min_length]
        baseline_aligned = baseline[:min_length]
        
        # Calculate RMSE
        squared_diff = (current_aligned - baseline_aligned) ** 2
        mean_squared_error = np.mean(squared_diff)
        rmse = np.sqrt(mean_squared_error)
        
        return float(rmse)
    except Exception as e:
        print(f"Error calculating RMSE: {e}")
        return None


@db_session
def get_baseline_pressure_profiles(machine_id):
    """
    Get all baseline pressure profiles for a machine
    """
    try:
        from models import PressureLogFile, db as pony_db
        
        # Get all baseline log files for this machine
        baseline_logs = PressureLogFile.select(
            lambda p: p.machine_id == machine_id and p.baseline == True
        )[:]
        
        baseline_profiles = []
        for log in baseline_logs:
            # Get pressure data for this log file
            query = """
            SELECT pressure_value 
            FROM tiei_sample_4.pressure_sensor_data 
            WHERE log_file_id = %s 
            ORDER BY timestamp
            """
            pg_cursor.execute(query, (log.id,))
            pressure_values = [row[0] for row in pg_cursor.fetchall()]
            baseline_profiles.append({
                'log_id': log.id,
                'pressure_values': pressure_values
            })
        
        return baseline_profiles
    except Exception as e:
        print(f"Error getting baseline profiles: {e}")
        return []


@db_session
def check_first_log_for_machine(machine_id):
    """
    Check if this is the first log file for a machine
    """
    try:
        from models import PressureLogFile
        
        existing_logs = PressureLogFile.select(
            lambda p: p.machine_id == machine_id
        ).count()
        
        return existing_logs == 0
    except Exception as e:
        print(f"Error checking first log: {e}")
        return False


# ==========================================================
# LOG FILE
# ==========================================================

@db_session
def get_or_create_log_file(machine_id, file_name, pressure_stats):

    machine = PressureMonitoringMachine.get(
        id=machine_id
    )

    if machine is None:

        raise Exception(
            f"Machine {machine_id} not found."
        )

    # Extract timestamp from filename
    file_timestamp = extract_timestamp_from_filename(file_name)

    log = PressureLogFile.get(

        machine_id=machine_id,

        file_name=file_name

    )

    if log:

        print(
            f"Existing Log File ID : {log.id}"
        )

        return log.id

    # Check if this is the first log for this machine
    is_first_log = check_first_log_for_machine(machine_id)
    
    # Set baseline to True for first log, False otherwise
    baseline_flag = True if is_first_log else False
    
    if is_first_log:
        print(f"First log for machine {machine_id} - setting as baseline")

    log = PressureLogFile(

        machine_id=machine_id,

        file_name=file_name,

        time_stamp=file_timestamp,
        
        baseline=baseline_flag,
        
        mean_pressure=pressure_stats['mean_pressure'],
        
        peak_pressure=pressure_stats['peak_pressure'],
        
        start_time=pressure_stats['start_time'],
        
        end_time=pressure_stats['end_time'],
        
        cycle_duration_seconds=pressure_stats['cycle_duration_seconds'],
        
        pressure_ripple=pressure_stats['pressure_ripple']

    )

    commit()

    print(
        f"Created Log File ID : {log.id}"
    )
    
    if file_timestamp:
        print(f"File Timestamp : {file_timestamp}")
    
    print(f"Statistics - Mean: {pressure_stats['mean_pressure']:.2f}, Peak: {pressure_stats['peak_pressure']:.2f}, "
          f"Duration: {pressure_stats['cycle_duration_seconds']:.2f}s, Ripple: {pressure_stats['pressure_ripple']:.2f}")
    
    if baseline_flag:
        print("Baseline: True")
    else:
        print("Baseline: False")

    return log.id


@db_session
def update_log_file_rmse(log_file_id, rmse_value):
    """
    Update RMSE value for a log file
    """
    try:
        from models import PressureLogFile
        
        log = PressureLogFile.get(id=log_file_id)
        if log:
            log.rmse = rmse_value
            commit()
            print(f"Updated RMSE for log {log_file_id}: {rmse_value:.4f}")
    except Exception as e:
        print(f"Error updating RMSE: {e}")



# ==========================================================
# DATABASE INSERT
# ==========================================================

def insert_data(df, machine, log_file_id):

    inserted = 0

    try:

        for _, row in df.iterrows():

            try:

                timestamp = pd.to_datetime(
                    row["timestamp"]
                ).to_pydatetime()

                pressure_value = float(
                    row["pressure_value"]
                )

                pg_cursor.execute(
                    """
                    INSERT INTO tiei_sample_4.pressure_sensor_data
                    (
                        timestamp,
                        pressure_value,
                        machine_id,
                        log_file_id
                    )
                    VALUES
                    (%s, %s, %s, %s)
                    """,
                    (
                        timestamp,
                        pressure_value,
                        machine["machine_id"],
                        log_file_id
                    )
                )

                inserted += 1

            except Exception as row_error:

                print(
                    f"Row Error : {row_error}"
                )

        pg_conn.commit()

        print(
            f"Inserted Rows : {inserted}"
        )

    except Exception as e:

        pg_conn.rollback()

        print(
            f"Database Insert Error : {e}"
        )


# ==========================================================
# PROCESS FILE
# ==========================================================

def process_file(machine, filename, file_time):

    try:

        print("\n==========================================")
        print(f"Machine    : {machine['machine_name']}")
        print(f"Processing : {filename}")
        print("==========================================")

        # ----------------------------------
        # Copy latest CSV
        # ----------------------------------

        local_file = copy_to_latest(
            machine,
            filename
        )

        # ----------------------------------
        # Read CSV
        # ----------------------------------

        df = pd.read_csv(
            local_file,
            encoding="cp932",
            skiprows=1
        )

        # ----------------------------------
        # Rename Columns
        # ----------------------------------

        df.rename(
            columns={
                "タイムスタンプ(yyyy/mm/dd hh:mm:ss.fff)": "timestamp",
                machine["pressure_column"]: "pressure_value"
            },
            inplace=True
        )

        print("\nColumns Found")

        print(df.columns.tolist())

        print("\nFirst 5 Records")

        print(df.head())

        # ----------------------------------
        # Calculate Pressure Statistics
        # ----------------------------------

        pressure_stats = calculate_pressure_statistics(df)
        
        if not pressure_stats:
            print("Failed to calculate pressure statistics")
            return

        print("\nPressure Statistics:")
        print(f"  Mean Pressure: {pressure_stats['mean_pressure']:.2f}")
        print(f"  Peak Pressure: {pressure_stats['peak_pressure']:.2f}")
        print(f"  Start Time: {pressure_stats['start_time']}")
        print(f"  End Time: {pressure_stats['end_time']}")
        print(f"  Cycle Duration: {pressure_stats['cycle_duration_seconds']:.2f} seconds")
        print(f"  Pressure Ripple: {pressure_stats['pressure_ripple']:.2f}")

        # ----------------------------------
        # Create/Get Log File with statistics
        # ----------------------------------

        log_file_id = get_or_create_log_file(
            machine["machine_id"],
            filename,
            pressure_stats
        )

        print(
            f"\nLog File ID : {log_file_id}"
        )

        # ----------------------------------
        # Insert Pressure Data
        # ----------------------------------

        insert_data(
            df,
            machine,
            log_file_id
        )

        # ----------------------------------
        # Calculate RMSE if not baseline
        # ----------------------------------
        
        # Check if this log is not a baseline
        @db_session
        def check_and_calculate_rmse():
            from models import PressureLogFile
            log = PressureLogFile.get(id=log_file_id)
            
            if log and not log.baseline:
                print("\nCalculating RMSE against baseline profiles...")
                
                # Get current pressure values
                current_pressure = df['pressure_value'].values.tolist()
                
                # Get baseline profiles for this machine
                baseline_profiles = get_baseline_pressure_profiles(machine["machine_id"])
                
                if baseline_profiles:
                    # Calculate RMSE against each baseline and use the minimum
                    rmse_values = []
                    for baseline_profile in baseline_profiles:
                        baseline_pressure = baseline_profile['pressure_values']
                        if baseline_pressure:
                            rmse = calculate_rmse(current_pressure, baseline_pressure)
                            if rmse is not None:
                                rmse_values.append(rmse)
                                print(f"  RMSE vs baseline {baseline_profile['log_id']}: {rmse:.4f}")
                    
                    if rmse_values:
                        # Use the minimum RMSE (best match)
                        min_rmse = min(rmse_values)
                        update_log_file_rmse(log_file_id, min_rmse)
                        print(f"  Final RMSE (best match): {min_rmse:.4f}")
                        
                        # Process RMSE-based corrective activity tracking
                        process_rmse_corrective_activity(machine["machine_id"], min_rmse, log_file_id)
                    else:
                        print("  No baseline profiles found for RMSE calculation")
                else:
                    print("  No baseline profiles found for RMSE calculation")
            else:
                print("\nBaseline log - skipping RMSE calculation")

        check_and_calculate_rmse()

        # ----------------------------------
        # Save Last Processed with timestamp
        # ----------------------------------

        save_last_processed(
            machine,
            filename,
            file_time
        )

        print(
            f"\nCompleted : {filename}"
        )

    except Exception as e:

        print(
            f"\nProcess Error : {e}"
        )


# ==========================================================
# SETUP MACHINE CONFIG
# ==========================================================

def setup_machine_config(args):
    """
    Setup machine configuration based on command line arguments
    """
    if args.machine_id:
        # Filter machines to only include the specified machine
        machines = [m for m in MACHINES if m['machine_id'] == args.machine_id]
        if not machines:
            raise ValueError(f"Machine ID {args.machine_id} not found in configuration")
        
        machine = machines[0]
        
        # Override configuration with command line arguments
        if args.os == 'linux':
            if args.ip_address:
                machine['ip_address'] = args.ip_address
            if args.mount_location:
                machine['mount_location'] = args.mount_location
            # Update watch_folder to use mount location
            if args.mount_location:
                machine['watch_folder'] = args.mount_location
        else:
            # Windows mode - use local directory
            if args.local_directory:
                machine['watch_folder'] = args.local_directory
        
        return [machine]
    
    # If no machine_id specified, use all machines
    return MACHINES


# ==========================================================
# MAIN
# ==========================================================

def main():
    """
    Main function to start pressure data monitoring
    """
    
    # Parse command line arguments
    args = parse_arguments()
    
    print("\n==========================================")
    print(" Toyota Pressure Collector Started")
    print("==========================================\n")
    
    print(f"Operating System : {args.os}")
    print(f"Skip Mount       : {args.skip_mount}")
    
    # Setup machine configuration based on arguments
    machines = setup_machine_config(args)
    
    for machine in machines:

        print(
            f"Machine : {machine['machine_name']}"
        )

        print(
            f"Folder  : {machine['watch_folder']}"
        )
        
        if args.os == 'linux':
            print(f"IP Address : {machine.get('ip_address', 'N/A')}")
            print(f"Mount Location : {machine.get('mount_location', 'N/A')}")

        print("------------------------------------------")

    print()

    # Mount shared drive for Linux
    if args.os == 'linux' and not args.skip_mount:
        for machine in machines:
            directory = Path(machine['watch_folder'])
            ip_address = machine.get('ip_address')
            mount_location = machine.get('mount_location')
            
            if ip_address and mount_location:
                print(f"\nChecking for shared drive for {machine['machine_name']}")
                
                while True:
                    try:
                        if not check_for_mount_drive(directory, ip_address=ip_address, mount_location=mount_location):
                            print(f"Mounting drive for {machine['machine_name']}")
                            if mount_shared_drive(ip_address=ip_address, mount_location=mount_location):
                                print(f"Checking for shared drive, again!")
                                if check_for_mount_drive(directory):
                                    print(f"Mounted the shared folder drive for {machine['machine_name']}")
                                    break
                                print(f"Not Able to Mount the shared folder, check the network")
                                time.sleep(5)
                            else:
                                print(f"Mount failed, retrying in 5 sec...")
                                time.sleep(5)
                        else:
                            print(f"Already Mounted for {machine['machine_name']}")
                            break
                    except Exception as error:
                        print(f"Mount error for {machine['machine_name']}: {error}")
                        print(f"Sleeping for 5 sec...")
                        time.sleep(5)
    elif args.skip_mount:
        print("Skipping mount operations (Docker mode)")

    # Start monitoring loop
    while True:

        try:

            for machine in machines:

                # Get last processed filename and timestamp
                last_filename, last_time = get_last_processed(machine)

                # Get all new files since last processed time
                new_files = get_new_files(machine, last_time)

                if new_files:

                    print(
                        f"{machine['machine_name']} : Found {len(new_files)} new files to process"
                    )

                    # Process each file in order
                    for filename, file_time in new_files:
                        process_file(machine, filename, file_time)
                else:

                    print(
                        f"{machine['machine_name']} : No New Files"
                    )

            time.sleep(
                POLL_INTERVAL
            )

        except KeyboardInterrupt:

            print("\nCollector Stopped.")
            
            # Unmount drives on Linux
            if args.os == 'linux' and not args.skip_mount:
                for machine in machines:
                    mount_location = machine.get('mount_location')
                    if mount_location:
                        unmount_drive(mount_location)

            break

        except Exception as e:

            print(
                f"\nMain Loop Error : {e}"
            )

            time.sleep(
                POLL_INTERVAL
            )


if __name__ == "__main__":

    main()
