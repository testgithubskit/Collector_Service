#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
TRANSFORMATION MODULE
================================

Module that contains functions to transforms log file to extract required machine data

This script requires the following modules be installed in the python environment

    Standard Library
    =================

    * logging - to perform logging operations
    * pathlib - To work with files and directories
    * time - To work with time objects
    * datetime - To work with datetime objects
    * csv - To work with csv files

    Related 3rd Party Library
    =============================

    * pandas - To work with dataframes
    * numpy - To work with arrays

This script contains the following function
    * extract_static_data - Main function to call appropriate functions to test out monitoring function
    * transform_log_files - Main function to call appropriate functions to test out monitoring function
    * main - Main function to call appropriate functions to test out the transformation functions
"""

# Standard library imports
import logging
from pathlib import Path
import time
import datetime
import csv
import os
import subprocess

# Related third party imports
import pandas as pd
import numpy as np
import dateparser

# Local application/library specific imports
from app.data_transformation_services import COLUMN_HEADER
from app.file_system_operation import MONITORING_DIRECTORY, MONITORING_DIRECTORY_2
from app.database.crud_operations import get_machine_parameters, get_machine_parameters_type, \
    select_activities_by_machine_params_condition, update_corrective_activities_from_dataframe, \
    get_latest_log_id, insert_spm_log_file
from app.anomaly_detection.detection_algorithm import check_dynamic_condition
from app.database.db_utils import get_parameters_limits_timescaledb, get_parameters_name_id_timescaledb
from app.report_manager.report_summary_generator import create_excel_report

__author__ = "smt18m005@iiitdm.ac.in"

LOGGER = logging.getLogger(__name__)


def extract_static_data(directory: Path) -> dict:
    """
    EXTRACT STATIC DATA
    =======================

    This function is used to extract static data such as date time, seat diameter from the log file (these data
    typically don't have or require timestamp, these are part of every cycle and will not be changing during
    process.

    :return: A dictionary of key value pairs consisting of parameter name (interger id from database) and value
    """

    static_machine_data = {}

    # command_to_ping = ["ping", "-c", "1", "172.18.20.27"]
    # host_status = subprocess.call(command_to_ping)
    # if host_status != 0:
    #     raise ConnectionError("Host 172.18.20.27 is unreachable, try again!")

    if not os.path.exists(directory):
        raise FileNotFoundError("Path does not exist, check if shared drive is mounted")

    with open(directory, "r", encoding="latin-1") as machine_data_file:
        # Creating the file reader object
        csv_reader = csv.reader(machine_data_file)

        # Skipping the first row
        next(csv_reader)  # 0th Row
        part_number = next(csv_reader)[1]  # 1st Row
        next(csv_reader)  # 2nd Row

        # The next two rows consist of data and time in the log file
        cycle_start_time = next(csv_reader)[1] + " " + next(csv_reader)[1] + "+0530"  # 3rd & 4th Row

        # Converting the string of time to time object
        cycle_start_time = time.strptime(cycle_start_time, "%Y/%m/%d %H:%M:%S%z")

        # Converting to datetime for subsequent usage
        cycle_start_time = datetime.datetime(*cycle_start_time[:6])

        # Converting to numpy.datetime64 for subsequent usage
        cycle_start_time = np.datetime64(cycle_start_time)

        # Data for Part Production Table
        static_machine_data['time'] = cycle_start_time
        static_machine_data['part_number'] = part_number

        # Data for Static Event Parameter Table
        static_machine_data['time'] = cycle_start_time
        static_machine_data['part_number'] = part_number

        # This range has to be changed based on the parameter id in database
        for i in range(1, 23):
            static_machine_data[i] = next(csv_reader)[1]  # 5th Row,  end of loop # 26th Row

    LOGGER.debug(static_machine_data)
    return static_machine_data


def transform_log_files(directory: Path) -> tuple:
    """
    TRANSFORM LOG FILES
    ====================

    This function is used to extract real time data from the log file, these are parameters that will change during the
    processing and hence need timestamp (they are generated time stamp based on assumption that every record is created
    40 milli second

    :return: List of real time machine parameters
    """
    #
    # command_to_ping = ["ping", "-c", "1", "172.18.20.27"]
    # host_status = subprocess.call(command_to_ping)

    # if host_status != 0:
    #     raise ConnectionError("Host 172.18.20.27 is unreachable, try again!")

    if not os.path.exists(directory):
        raise FileNotFoundError("Path does not exist, check if shared drive is mounted")

    # Opening the csv file to extract the cycle start date and time
    with open(directory, "r", encoding="latin-1") as machine_data_file:
        # Creating the file reader object
        csv_reader = csv.reader(machine_data_file)

        # Skipping the first 3 rows
        [next(csv_reader) for _ in range(3)]

        # The next row contains date and then the time
        # Adding timezone by concatenating +0530
        cycle_start_time = next(csv_reader)[1] + " " + next(csv_reader)[1] + "+0530"

    # Reading the csv file as pandas dataframe, skipping the first 28 rows ( as they represent the static data)
    # Using the above declared parameters as the required columns
    machine_data = pd.read_csv(directory, skiprows=28, usecols=COLUMN_HEADER, encoding="latin1")

    # Changing the column names (parameter names) from declared string values to the index values in their
    # Respective table in database, refer to "tiei_sample_2.machine_parameters" table
    machine_data.columns = [23, 24, 25, 26, 27, 28, 29]

    # Converting from string to "time.struct_time" for subsequent usage
    cycle_start_time = time.strptime(cycle_start_time, "%Y/%m/%d %H:%M:%S%z")

    # Converting to datetime for subsequent usage
    cycle_start_time = datetime.datetime(*cycle_start_time[:6])

    # Converting to numpy.datetime64 for subsequent usage
    cycle_start_time = np.datetime64(cycle_start_time)

    # Creating timestamp for each row of the data (since it is not added by default)
    # This is created by adding 40ms for each consecutive row from the start time of the cycle
    # This 40s is based on user input (machine's scanning frequency)
    generated_timestamp = [cycle_start_time + np.timedelta64(40 * i, 'ms') for i in range(machine_data.shape[0])]

    # Creating new column to the machine data frame called "time" with previously created values
    machine_data["time"] = generated_timestamp

    # Reordering the columns such that time and then machine id comes first just like in the database schema
    machine_data = machine_data.iloc[:, [7, 0, 1, 2, 3, 4, 5, 6]]

    # Converting the wide table to narrow (long) table, so that it could be fit into the database schema
    # Instead of saving the data with time, parameter1, parameter2, etc (represent column name)
    # We save it as time, parameter name, value (hence there will be multiple copies of the same timestamp
    machine_data = pd.melt(frame=machine_data, id_vars=["time"],
                           var_name="machine_parameters_id", value_name="value")

    # Converting the machine data to numpy and then to list
    machine_data = machine_data.to_numpy().tolist()
    return machine_data, generated_timestamp[-1]


def transform_log_files_laser_active(directory: Path,
                                     next_alert_time_for_all_signals: dict = {}) -> tuple:
    """
    TRANSFORM LOG FILES
    ====================

    This function is used to extract real time data from the log file, these are parameters that will change during the
    processing and hence need timestamp (they are generated time stamp based on assumption that every record is created
    40 milli second

    :return: List of real time machine parameters
    """
    #
    # command_to_ping = ["ping", "-c", "1", "172.18.20.27"]
    # host_status = subprocess.call(command_to_ping)

    # if host_status != 0:
    #     raise ConnectionError("Host 172.18.20.27 is unreachable, try again!")

    if not os.path.exists(directory):
        raise FileNotFoundError("Path does not exist, check if shared drive is mounted")

    # Opening the csv file to extract the cycle start date and time
    with open(directory, "r", encoding="latin-1") as machine_data_file:
        # Creating the file reader object
        csv_reader = csv.reader(machine_data_file)

        # Skipping the first 3 rows
        [next(csv_reader) for _ in range(3)]

        # The next row contains date and then the time
        # Adding timezone by concatenating +0530
        cycle_start_time = next(csv_reader)[1] + " " + next(csv_reader)[1] + "+0530"

    # Reading the csv file as pandas dataframe, skipping the first 28 rows ( as they represent the static data)
    # Using the above declared parameters as the required columns
    machine_data = pd.read_csv(directory, skiprows=28, usecols=COLUMN_HEADER, encoding="latin1")

    # Changing the column names (parameter names) from declared string values to the index values in their
    # Respective table in database, refer to "tiei_sample_2.machine_parameters" table
    machine_data.columns = [23, 24, 25, 26, 27, 28, 29]

    # Converting from string to "time.struct_time" for subsequent usage
    cycle_start_time = time.strptime(cycle_start_time, "%Y/%m/%d %H:%M:%S%z")

    # Converting to datetime for subsequent usage
    cycle_start_time = datetime.datetime(*cycle_start_time[:6])

    # Converting to numpy.datetime64 for subsequent usage
    cycle_start_time = np.datetime64(cycle_start_time)

    # Creating timestamp for each row of the data (since it is not added by default)
    # This is created by adding 40ms for each consecutive row from the start time of the cycle
    # This 40s is based on user input (machine's scanning frequency)
    generated_timestamp = [cycle_start_time + np.timedelta64(40 * i, 'ms') for i in range(machine_data.shape[0])]

    # Creating new column to the machine data frame called "time" with previously created values
    machine_data["time"] = generated_timestamp

    # Reordering the columns such that time and then machine id comes first just like in the database schema
    machine_data = machine_data.iloc[:, [7, 0, 1, 2, 3, 4, 5, 6]]

    static_ids = [23, 24]
    dynamic_parameters_ids = [25, 26, 27, 28, 29]

    static_parameters_ids = ["time"]
    static_parameters_ids.extend(static_ids)

    # Static Parameters
    machine_data_static = machine_data[static_parameters_ids].copy()

    machine_data_static_active = machine_data_static.tail(1)

    machine_data_static = pd.melt(frame=machine_data_static, id_vars=["time"],
                                  var_name="machine_parameters_id", value_name="value")

    machine_data_static_active = pd.melt(frame=machine_data_static_active, id_vars=["time"],
                                         var_name="machine_parameters_id", value_name="value")

    machine_data_static["condition"] = 1
    machine_data_static_active["condition"] = 1
    machine_data_static["parameter_name"] = machine_data_static["machine_parameters_id"]

    machine_data_static["warning_limit"] = machine_data_static["machine_parameters_id"]
    machine_data_static_active["warning_limit"] = machine_data_static_active["machine_parameters_id"]

    machine_data_static["critical_limit"] = machine_data_static["machine_parameters_id"]
    machine_data_static_active["critical_limit"] = machine_data_static_active["machine_parameters_id"]

    data_warning_mapping, data_critical_mapping = get_parameters_limits_timescaledb()
    parameter_name_mapping = get_parameters_name_id_timescaledb()

    machine_data_static["warning_limit"] = machine_data_static["warning_limit"].map(data_warning_mapping)
    machine_data_static["parameter_name"] = machine_data_static["parameter_name"].map(parameter_name_mapping)
    machine_data_static_active["warning_limit"] = machine_data_static_active["warning_limit"].map(data_warning_mapping)

    machine_data_static["critical_limit"] = machine_data_static["critical_limit"].map(data_critical_mapping)
    machine_data_static_active["critical_limit"] = machine_data_static_active["critical_limit"]. \
        map(data_critical_mapping)

    machine_data_static["condition"] = np.where(
        (machine_data_static["value"] >= machine_data_static["critical_limit"]),
        3, machine_data_static["condition"])

    machine_data_static_active["condition"] = np.where(
        (machine_data_static_active["value"] >= machine_data_static_active["critical_limit"]),
        3, machine_data_static_active["condition"])

    machine_data_static["condition"] = np.where(
        (machine_data_static["value"] >= machine_data_static["warning_limit"]) &
        (machine_data_static["value"] < machine_data_static["critical_limit"]),
        2, machine_data_static["condition"])

    machine_data_static_active["condition"] = np.where(
        (machine_data_static_active["value"] >= machine_data_static_active["warning_limit"]) &
        (machine_data_static_active["value"] < machine_data_static_active["critical_limit"]),
        2, machine_data_static_active["condition"])

    current_anomaly_static = machine_data_static[(machine_data_static["condition"] == 3)]

    new_static_anomaly_list = None

    if not current_anomaly_static.empty:

        new_static_anomaly, next_alert_update = check_for_new_anomaly(current_anomaly_static,
                                                                      next_alert_time_for_all_signals)

        next_alert_time_for_all_signals = next_alert_update

        if not new_static_anomaly.empty:
            new_static_anomaly_list = new_static_anomaly.values.tolist()

    machine_data_static_active = machine_data_static_active.loc[:, ["time", "machine_parameters_id",
                                                                    "value", "condition"]]
    machine_data_active_list = machine_data_static_active.to_numpy().tolist()

    # Dynamic Parameters
    machine_data_dynamic = []

    for dynamic_parameter in dynamic_parameters_ids:
        df_dynamic = machine_data[['time', dynamic_parameter]].copy()
        df_dynamic["machine_parameters_id"] = dynamic_parameter
        df_dynamic["condition"] = None
        df_dynamic.rename(columns={dynamic_parameter: 'value'}, inplace=True)
        df_dynamic_data = machine_data[[dynamic_parameter]].to_numpy().tolist()
        df_dynamic_data = [d[0] for d in df_dynamic_data]

        parameter_dynamic_condition = check_dynamic_condition(dynamic_parameter, df_dynamic_data)

        df_dynamic.iloc[-1, df_dynamic.columns.get_loc("condition")] = parameter_dynamic_condition

        df_dynamic = df_dynamic.loc[:, ["time", "machine_parameters_id", "value", "condition"]]

        machine_data_dynamic.append(df_dynamic)

    machine_data_dynamic_df = pd.concat(machine_data_dynamic, ignore_index=True)

    machine_data_dynamic_df["parameter_name"] = machine_data_dynamic_df["machine_parameters_id"]
    machine_data_dynamic_df["parameter_name"] = machine_data_dynamic_df["parameter_name"].map(parameter_name_mapping)

    current_anomaly_dynamic = machine_data_dynamic_df[(machine_data_dynamic_df["condition"] == 3)]

    new_dynamic_anomaly_list = None

    if not current_anomaly_dynamic.empty:

        new_dynamic_anomaly, next_alert_update = check_for_new_anomaly(current_anomaly_dynamic,
                                                                       next_alert_time_for_all_signals)

        next_alert_time_for_all_signals = next_alert_update

        if not new_dynamic_anomaly.empty:
            new_dynamic_anomaly_list = new_dynamic_anomaly.values.tolist()

    file_location = "D:\\PS-CMTI\\Codes\\PycharmProjects\\TIEI Master" \
                    "\\Laser Cladding\\laser_clad_main\\output" + "\\SPM_ANOMALY_LASER_CLADDING.xlsx"

    if new_static_anomaly_list or new_dynamic_anomaly_list:
        create_excel_report(file_location=file_location, machine_name="Laser Cladding",
                            static_data=new_static_anomaly_list, dynamic_data=new_dynamic_anomaly_list)

    machine_data_dynamic_active_df = machine_data_dynamic_df[machine_data_dynamic_df['condition'].notna()]

    machine_data_dynamic_active_df = machine_data_dynamic_active_df[["time", "machine_parameters_id",
                                                                     "value", "condition"]]

    machine_data_dynamic_active_list = machine_data_dynamic_active_df.to_numpy().tolist()

    machine_data_active_list.extend(machine_data_dynamic_active_list)

    machine_data_list = pd.concat([machine_data_dynamic_df, machine_data_static], ignore_index=True)
    machine_data_list = machine_data_list[["time", "machine_parameters_id", "value", "condition"]]
    machine_data_list = machine_data_list.values.tolist()

    return machine_data_list, generated_timestamp[-1], machine_data_active_list, next_alert_time_for_all_signals


def transform_log_files_spm_2_grinder(directory: Path, machine_id: int) -> list:
    """
    TRANSFORM LOG FILES SPM_2 GRINDER
    ======================================

    This function is used to extract real time data from the log file, these are parameters that will change during the
    processing and hence need timestamp (they are generated time stamp based on assumption that every record is created
    40 milli second

    :return: List of real time machine parameters
    """
    #
    # command_to_ping = ["ping", "-c", "1", "172.18.20.27"]
    # host_status = subprocess.call(command_to_ping)
    #
    # if host_status != 0:
    #     raise ConnectionError("Host 172.18.20.27 is unreachable, try again!")
    #
    # if not os.path.exists(directory):
    #     raise FileNotFoundError("Path does not exist, check if shared drive is mounted")

    # Opening the csv file to extract the cycle start date and time
    # with open(directory, "r", encoding="latin-1") as machine_data_file:
    #     # Creating the file reader object
    #     csv_reader = csv.reader(machine_data_file)
    #
    #     # Skipping the first 3 rows
    #     [next(csv_reader) for _ in range(3)]
    #
    #     # The next row contains date and then the time
    #     # Adding timezone by concatenating +0530
    #     cycle_start_time = next(csv_reader)[1] + " " + next(csv_reader)[1] + "+0530"

    # Reading the csv file as pandas dataframe, skipping the first 10 rows ( as they represent the static data)
    # Using the above declared parameters as the required columns
    machine_data = pd.read_csv(directory, skiprows=10, usecols=[i for i in range(1, 17)], encoding="latin1")

    # Changing the column names (parameter names) from declared string values to the index values in their
    # Respective table in database, refer to "tiei_sample_2.machine_parameters" table
    machine_data.columns = [f"{i}" for i in range(1, 17)]

    print(machine_data.dtypes)

    machine_data['1'] = machine_data['1'].astype(str)
    machine_data['2'] = machine_data['2'].astype(str)
    print(machine_data.dtypes)

    machine_data['time'] = machine_data["1"] + "T" + machine_data["2"]
    machine_data['time'] = pd.to_datetime(machine_data['time'], errors='coerce', format='%Y%m%dT%H%M%S.%f')

    machine_data = machine_data.drop(machine_data.iloc[:, :2], axis=1)

    # Reordering the columns such that time and then machine id comes first just like in the database schema

    required_columns = [14]
    required_columns.extend([i for i in range(0, 14)])

    machine_data = machine_data.iloc[:, required_columns]

    parameters_ids = get_machine_parameters(machine_id=machine_id)

    columns = ["time"]
    columns.extend(parameters_ids)
    print("OK 1")
    machine_data.columns = columns
    print("OK 2")

    # Converting the wide table to narrow (long) table, so that it could be fit into the database schema
    # Instead of saving the data with time, parameter1, parameter2, etc (represent column name)
    # We save it as time, parameter name, value (hence there will be multiple copies of the same timestamp
    machine_data = pd.melt(frame=machine_data, id_vars=["time"],
                           var_name="machine_parameters_id", value_name="value")

    print("OK")

    # Converting the machine data to numpy and then to list
    machine_data = machine_data.to_numpy().tolist()

    return machine_data

def transform_log_files_spm_2_active(directory: Path, machine_id: int,
                                     next_alert_time_for_all_signals: dict = {}) -> tuple[list, list, dict]:
    """
    TRANSFORM LOG FILES SPM_2 GRINDER
    ======================================

    This function is used to extract real time data from the log file, these are parameters that will change during the
    processing and hence need timestamp (they are generated time stamp based on assumption that every record is created
    40 milli second

    :return: tuple of List of real time machine parameters and real time active parameters data
    """

    command_to_ping = ["ping", "-c", "1", "10.82.126.72"]

    host_status = subprocess.call(command_to_ping)

    if host_status != 0:
        raise ConnectionError("Host 10.82.126.72 is unreachable, try again!")

    if not os.path.exists(directory):
        raise FileNotFoundError("Path does not exist, check if shared drive is mounted")

    parameters_ids = get_machine_parameters(machine_id=machine_id)
    total_parameters = len(parameters_ids) if parameters_ids else 0

    # ------------------------------------------------------------------
    # Step 1: Dynamically locate the English Header Row (ITEMNAME_ENG)
    # ------------------------------------------------------------------
    header_row_idx = None
    english_headers = None

    try:
        with open(directory, "r", encoding="latin1") as f:
            reader = csv.reader(f)
            for idx, row in enumerate(reader):
                if row and row[0] == "ITEMNAME_ENG":
                    header_row_idx = idx
                    english_headers = [c.strip() for c in row]
                    break
                if idx > 30:
                    break
    except Exception as e:
        LOGGER.error(f"Error reading file structure for {directory}: {e}")
        return []

    # ------------------------------------------------------------------
    # Step 2: Read CSV and parse timestamps
    # ------------------------------------------------------------------
    try:
        if header_row_idx is not None and english_headers:
            # Data starts 2 rows after ITEMNAME_ENG (skipping the Units row)
            data_skiprows = header_row_idx + 2
            
            # Handle duplicate column names by making them unique
            seen_names = {}
            unique_headers = []
            for i, name in enumerate(english_headers):
                if name in seen_names:
                    seen_names[name] += 1
                    unique_headers.append(f"{name}_{seen_names[name]}")
                else:
                    seen_names[name] = 0
                    unique_headers.append(name)
            
            machine_data = pd.read_csv(
                directory,
                skiprows=data_skiprows,
                header=None,
                names=unique_headers,
                encoding="latin1"
            )

            # Combine Date and Time columns into ISO timestamp
            # Pad DataAcquisitionTime with leading zeros to handle midnight times
            # e.g., '102.074' becomes '000102.074' for 00:01:02.074
            # Check if log file spans more than 120 seconds using raw DataAcquisitionTime
            # Parse the time values to calculate span before full processing
            raw_times = machine_data['DataAcquisitionTime'].dropna().tolist()
            if raw_times:
                # Parse raw time strings to datetime for comparison
                # Format: HHMMSS.ffffff or HMMSS.ffffff (without leading zeros)
                parsed_times = []
                for t in raw_times:
                    t_str = str(t)
                    if '.' in t_str:
                        int_part, frac_part = t_str.split('.', 1)
                        int_part = int_part.zfill(6)  # Pad to HHMMSS
                        t_str = f"{int_part}.{frac_part}"
                    else:
                        t_str = t_str.zfill(6)
                    # Parse as time only (no date)
                    try:
                        time_obj = pd.to_datetime(t_str, format='%H%M%S.%f', errors='coerce')
                        parsed_times.append(time_obj)
                    except:
                        continue

                if parsed_times:
                    time_span = max(parsed_times) - min(parsed_times)
                    time_span_seconds = time_span.total_seconds()
                    LOGGER.info(f"Log file time span: {time_span_seconds:.2f} seconds")
                    if time_span_seconds > 100:
                        LOGGER.warning(f"Log file spans {time_span_seconds:.2f} seconds (> 100s), skipping processing")
                        return None, None, None, None

            # Pad DataAcquisitionTime with leading zeros to handle midnight times
            # e.g., '102.074' becomes '000102.074' for 00:01:02.074
            def pad_time_string(time_str):
                if pd.isna(time_str):
                    return time_str
                time_str = str(time_str)
                if '.' in time_str:
                    # Split into integer and fractional parts
                    int_part, frac_part = time_str.split('.', 1)
                    # Pad integer part to 6 digits (HHMMSS)
                    int_part = int_part.zfill(6)
                    return f"{int_part}.{frac_part}"
                else:
                    # No fractional part, pad to 6 digits
                    return time_str.zfill(6)

            machine_data['DataAcquisitionTime'] = machine_data['DataAcquisitionTime'].apply(pad_time_string)

            machine_data['time'] = (
                machine_data['DataAcquisitionDate'].astype(str) + "T" +
                machine_data['DataAcquisitionTime'].astype(str)
            )
            machine_data['time'] = pd.to_datetime(
                machine_data['time'], errors='coerce', format='%Y%m%dT%H%M%S.%f'
            )

            # Drop tag, date, and raw time columns
            cols_to_drop = [c for c in ['ITEMNAME_ENG', 'DataAcquisitionDate', 'DataAcquisitionTime'] if c in machine_data.columns]
            machine_data = machine_data.drop(columns=cols_to_drop)

            # ------------------------------------------------------------------
            # Step 3: Map Columns to Database Parameter IDs (By Name first)
            # ------------------------------------------------------------------
            from app.database.crud_operations import execute_read_query_timescaledb
            query = f"""
                SELECT name, id 
                FROM tiei_sample_4.machine_parameters 
                WHERE machine_id = {machine_id}
                ORDER BY id;
            """
            param_records = execute_read_query_timescaledb(query)
            name_to_id = {row[0].strip(): row[1] for row in param_records} if param_records else {}

            # Map matching column names to parameter IDs using substring matching
            mapped_cols = {"time": "time"}
            for col in machine_data.columns:
                if col == "time":
                    continue
                # Try exact match first
                if col in name_to_id:
                    mapped_cols[col] = name_to_id[col]
                else:
                    # Try substring matching - check if CSV name is contained in database name
                    for db_name, param_id in name_to_id.items():
                        if col in db_name or db_name in col:
                            mapped_cols[col] = param_id
                            LOGGER.info(f"Substring match: CSV column '{col}' matched to DB name '{db_name}' → param_id {param_id}")
                            break

            # If name mapping found matches, use it; otherwise fallback to positional
            if len(mapped_cols) > 1:
                machine_data = machine_data[list(mapped_cols.keys())].rename(columns=mapped_cols)
            else:
                # Positional fallback for legacy configurations
                available_cols = [c for c in machine_data.columns if c != "time"]
                num_to_map = min(len(available_cols), total_parameters)
                positional_map = {"time": "time"}
                for i in range(num_to_map):
                    positional_map[available_cols[i]] = parameters_ids[i]
                machine_data = machine_data[list(positional_map.keys())].rename(columns=positional_map)

        else:
            # Fallback to original parsing if ITEMNAME_ENG was not found
            if machine_id == 61:
                columns = [i for i in range(1, total_parameters + 2)]
                columns.append(total_parameters + 3)
                machine_data = pd.read_csv(directory, skiprows=11, usecols=columns, encoding="latin1")
            else:
                machine_data = pd.read_csv(directory, skiprows=11, usecols=[i for i in range(1, total_parameters + 3)],
                                           encoding="latin1")

            machine_data.columns = [f"{i}" for i in range(1, total_parameters + 3)]
            machine_data['1'] = machine_data['1'].astype(str)
            machine_data['2'] = machine_data['2'].astype(str)
            machine_data['time'] = machine_data["1"] + "T" + machine_data["2"]
            machine_data['time'] = pd.to_datetime(machine_data['time'], errors='coerce', format='%Y%m%dT%H%M%S.%f')
            machine_data = machine_data.drop(machine_data.iloc[:, :2], axis=1)

            required_columns = [total_parameters]
            required_columns.extend([i for i in range(0, total_parameters)])
            machine_data = machine_data.iloc[:, required_columns]

            columns = ["time"]
            columns.extend(parameters_ids)
            machine_data.columns = columns

    except Exception as e:
        LOGGER.error(f"Error parsing log file {directory}: {e}")
        return []

    print("Raw Data after reading file: ")
    print(machine_data.tail())

    # Filter machine data to include only the starting 10 seconds of data
    if not machine_data.empty and machine_data['time'].notna().any():
        start_time = machine_data['time'].dropna().iloc[0]
        cutoff_time = start_time + pd.Timedelta(seconds=10)
        machine_data = machine_data[machine_data['time'] <= cutoff_time].copy()

    static_parameters_ids_temp = get_machine_parameters_type(machine_id=machine_id, parameter_type="spm_static")
    static_parameters_ids = ["time"]
    static_parameters_ids.extend([p for p in static_parameters_ids_temp if p in machine_data.columns])

    dynamic_parameters_ids = get_machine_parameters_type(machine_id=machine_id, parameter_type="spm_dynamic")
    dynamic_parameters_ids = [p for p in dynamic_parameters_ids if p in machine_data.columns]

    # Fetch parameter mappings needed for both static and dynamic processing
    data_warning_mapping, data_critical_mapping = get_parameters_limits_timescaledb()
    parameter_name_mapping = get_parameters_name_id_timescaledb()

    # ------------------------------------------------------------------
    # Dynamic Detection of AE Parameters for Log Tracking
    # ------------------------------------------------------------------
    # This must be defined before the dynamic parameter loop
    all_parameters = get_machine_parameters(machine_id=machine_id)
    
    # Filter parameters whose name contains "AE_GRAPH_SCAL_DP"
    log_tracking_params = [
        param_id for param_id in all_parameters
        if "AE_GRAPH_SCAL_DP" in parameter_name_mapping.get(param_id, "")
    ]
    LOGGER.info(f"Dynamic log tracking parameters for machine {machine_id}: {log_tracking_params}")

    print("OK_1")
    print(machine_data.tail())
    # Static Parameters
    machine_data_static = machine_data[static_parameters_ids].copy()

    machine_data_static_active = machine_data_static.tail(1)

    machine_data_static = pd.melt(frame=machine_data_static, id_vars=["time"],
                                  var_name="machine_parameters_id", value_name="value")

    machine_data_static_active = pd.melt(frame=machine_data_static_active, id_vars=["time"],
                                         var_name="machine_parameters_id", value_name="value")

    machine_data_static["condition"] = 1
    machine_data_static_active["condition"] = 1
    machine_data_static["parameter_name"] = machine_data_static["machine_parameters_id"]

    machine_data_static["warning_limit"] = machine_data_static["machine_parameters_id"]
    machine_data_static_active["warning_limit"] = machine_data_static_active["machine_parameters_id"]

    machine_data_static["critical_limit"] = machine_data_static["machine_parameters_id"]
    machine_data_static_active["critical_limit"] = machine_data_static_active["machine_parameters_id"]

    machine_data_static["warning_limit"] = machine_data_static["warning_limit"].map(data_warning_mapping)
    machine_data_static["parameter_name"] = machine_data_static["parameter_name"].map(parameter_name_mapping)
    machine_data_static_active["warning_limit"] = machine_data_static_active["warning_limit"].map(data_warning_mapping)

    machine_data_static["critical_limit"] = machine_data_static["critical_limit"].map(data_critical_mapping)
    machine_data_static_active["critical_limit"] = machine_data_static_active["critical_limit"]. \
        map(data_critical_mapping)

    machine_data_static["condition"] = np.where(
        (machine_data_static["value"] >= machine_data_static["critical_limit"]),
        3, machine_data_static["condition"])

    machine_data_static_active["condition"] = np.where(
        (machine_data_static_active["value"] >= machine_data_static_active["critical_limit"]),
        3, machine_data_static_active["condition"])

    machine_data_static["condition"] = np.where(
        (machine_data_static["value"] >= machine_data_static["warning_limit"]) &
        (machine_data_static["value"] < machine_data_static["critical_limit"]),
        2, machine_data_static["condition"])

    machine_data_static_active["condition"] = np.where(
        (machine_data_static_active["value"] >= machine_data_static_active["warning_limit"]) &
        (machine_data_static_active["value"] < machine_data_static_active["critical_limit"]),
        2, machine_data_static_active["condition"])

    current_anomaly_static = machine_data_static[(machine_data_static["condition"] == 3)]

    new_static_anomaly_list = None

    if not current_anomaly_static.empty:

        new_static_anomaly, next_alert_update = check_for_new_anomaly(current_anomaly_static,
                                                                      next_alert_time_for_all_signals)

        next_alert_time_for_all_signals = next_alert_update

        if not new_static_anomaly.empty:
            new_static_anomaly_list = new_static_anomaly.values.tolist()

    machine_data_static_active = machine_data_static_active.loc[:, ["time", "machine_parameters_id",
                                                                    "value", "condition"]]
    machine_data_active_list = machine_data_static_active.to_numpy().tolist()
    
    print("OK_2")
    print(machine_data_static.tail())
    # Dynamic Parameters
    machine_data_dynamic = []

    for dynamic_parameter in dynamic_parameters_ids:
        df_dynamic = machine_data[['time', dynamic_parameter]].copy()
        df_dynamic["machine_parameters_id"] = dynamic_parameter
        df_dynamic["condition"] = None
        df_dynamic.rename(columns={dynamic_parameter: 'value'}, inplace=True)
        df_dynamic_data = machine_data[[dynamic_parameter]].values.tolist()
        df_dynamic_data = [d[0] for d in df_dynamic_data]

        # Check if this is an AE parameter (log tracking parameter)
        # For AE parameters, use RMS value comparison with warning/critical limits
        # For other dynamic parameters, use Kruskal test against reference signal
        if dynamic_parameter in log_tracking_params:
            # AE parameter: calculate RMS value in 10-second window
            rms_value = None
            if df_dynamic_data:
                # Calculate RMS: sqrt(mean of squared values)
                rms_value = float(np.sqrt(np.mean(np.square(df_dynamic_data))))

            # Get warning and critical limits for this parameter
            warning_limit = data_warning_mapping.get(dynamic_parameter)
            critical_limit = data_critical_mapping.get(dynamic_parameter)

            # Determine condition based on RMS value comparison
            if rms_value is not None and critical_limit is not None:
                if rms_value >= critical_limit:
                    parameter_dynamic_condition = 3  # Critical
                elif warning_limit is not None and rms_value >= warning_limit:
                    parameter_dynamic_condition = 2  # Warning
                else:
                    parameter_dynamic_condition = 1  # OK
            else:
                parameter_dynamic_condition = 1  # Default to OK if limits not available

            LOGGER.info(f"AE Parameter {dynamic_parameter}: rms_value={rms_value}, warning={warning_limit}, critical={critical_limit}, condition={parameter_dynamic_condition}")
        else:
            # Non-AE dynamic parameter: use Kruskal test against reference signal
            parameter_dynamic_condition = check_dynamic_condition(dynamic_parameter, df_dynamic_data)

        df_dynamic.iloc[-1, df_dynamic.columns.get_loc("condition")] = parameter_dynamic_condition

        df_dynamic = df_dynamic.loc[:, ["time", "machine_parameters_id", "value", "condition"]]

        machine_data_dynamic.append(df_dynamic)

    machine_data_dynamic_df = pd.concat(machine_data_dynamic, ignore_index=True) if machine_data_dynamic else pd.DataFrame(columns=["time", "machine_parameters_id", "value", "condition"])

    machine_data_dynamic_df["parameter_name"] = machine_data_dynamic_df["machine_parameters_id"]
    machine_data_dynamic_df["parameter_name"] = machine_data_dynamic_df["parameter_name"].map(parameter_name_mapping)

    current_anomaly_dynamic = machine_data_dynamic_df[(machine_data_dynamic_df["condition"] == 3)]

    print("OK_3")
    print(machine_data_dynamic_df.tail())
    new_dynamic_anomaly_list = []

    if not current_anomaly_dynamic.empty:

        new_dynamic_anomaly, next_alert_update = check_for_new_anomaly(current_anomaly_dynamic,
                                                                       next_alert_time_for_all_signals)

        if next_alert_update:
            next_alert_time_for_all_signals = next_alert_update
            if not new_dynamic_anomaly.empty:
                new_dynamic_anomaly_list = new_dynamic_anomaly.values.tolist()

    #file_location = "D:\\PS-CMTI\\Codes\\PycharmProjects\\TIEI Master" \
    #                "\\Laser Cladding\\laser_clad_main\\output" + "\\SPM_ANOMALY.xlsx"

    #if new_static_anomaly_list or new_dynamic_anomaly_list:
    #
    #    create_excel_report(file_location=file_location, machine_name="SPM JOURNAL GRINDING",
    #                        static_data=new_static_anomaly_list, dynamic_data=new_dynamic_anomaly_list)

    machine_data_dynamic_active_df = machine_data_dynamic_df[machine_data_dynamic_df['condition'].notna()]
    
    print("OK_4")
    print(machine_data_dynamic_active_df)
    machine_data_dynamic_active_list = machine_data_dynamic_active_df.to_numpy().tolist()

    machine_data_active_list.extend(machine_data_dynamic_active_list)

    machine_data_list = pd.concat([machine_data_dynamic_df, machine_data_static], ignore_index=True)
    machine_data_list = machine_data_list[["time", "machine_parameters_id", "value", "condition"]]

    print("OK_5")
    print(machine_data_list.tail())
    LOGGER.info("Current Data Info:")
    LOGGER.info(machine_data_list.head())

    # ------------------------------------------------------------------
    # SPM Log File Tracking for AE Parameters
    # ------------------------------------------------------------------
    # log_tracking_params is already defined earlier (line 649) using dynamic detection
    # Get the initial time (first timestamp) for log file tracking
    if not machine_data_list.empty and 'time' in machine_data_list.columns and log_tracking_params:
        initial_time = machine_data_list['time'].dropna().iloc[0]
        LOGGER.info(f"Initial time for log tracking: {initial_time}")

        # Check if any of the log tracking parameters exist in the data
        df_log_params = machine_data_list[machine_data_list['machine_parameters_id'].isin(log_tracking_params)].copy()

        if not df_log_params.empty:
            LOGGER.info(f"Found data for log tracking parameters: {df_log_params['machine_parameters_id'].unique()}")

            # Get the latest log_id from spm_log_files table
            latest_log_id = get_latest_log_id()
            new_log_id = latest_log_id + 1
            LOGGER.info(f"New log_id for this processing: {new_log_id}")

            # Insert into spm_log_files table for each parameter
            for param_id in log_tracking_params:
                if param_id in df_log_params['machine_parameters_id'].values:
                    try:
                        # Calculate RMS for this parameter from the 10-second data window
                        param_data = df_log_params[df_log_params['machine_parameters_id'] == param_id]['value'].values
                        rms_value = None
                        if len(param_data) > 0:
                            # Calculate RMS: sqrt(mean of squared values)
                            rms_value = float(np.sqrt(np.mean(np.square(param_data))))
                            LOGGER.info(f"Calculated RMS for parameter {param_id}: {rms_value}")

                        insert_spm_log_file(log_id=new_log_id, machine_parameter_id=param_id, time=initial_time, rms=rms_value)
                        LOGGER.info(f"Inserted spm_log_file for parameter {param_id} with log_id {new_log_id}, rms={rms_value}")
                    except Exception as e:
                        LOGGER.error(f"Error inserting spm_log_file for parameter {param_id}: {e}")

            # Add log_id column to machine_data_list for these parameters
            # Create a mapping of parameter_id to log_id
            log_id_mapping = {param_id: new_log_id for param_id in log_tracking_params}
            LOGGER.info(f"DEBUG: log_id_mapping: {log_id_mapping}")
            LOGGER.info(f"DEBUG: machine_parameters_id unique values: {machine_data_list['machine_parameters_id'].unique()}")
            LOGGER.info(f"DEBUG: machine_parameters_id dtype: {machine_data_list['machine_parameters_id'].dtype}")

            # Convert machine_parameters_id to int for proper mapping
            machine_data_list['machine_parameters_id'] = pd.to_numeric(machine_data_list['machine_parameters_id'], errors='coerce').astype('Int64')
            LOGGER.info(f"DEBUG: After conversion - machine_parameters_id dtype: {machine_data_list['machine_parameters_id'].dtype}")

            machine_data_list['log_id'] = machine_data_list['machine_parameters_id'].map(log_id_mapping)
            LOGGER.info(f"DEBUG: After mapping - log_id column sample:\n{machine_data_list[['machine_parameters_id', 'log_id']].head(10)}")

            # Replace NaN with None for database compatibility
            machine_data_list['log_id'] = machine_data_list['log_id'].where(pd.notna(machine_data_list['log_id']), None)
            LOGGER.info(f"Added log_id column to machine_data_list for log tracking parameters")
        else:
            # No log tracking parameters found, set log_id to None for all
            machine_data_list['log_id'] = None
            LOGGER.info("No log tracking parameters found, log_id set to None for all rows")
    else:
        # No data or no time column, set log_id to None
        machine_data_list['log_id'] = None
        LOGGER.info("No data or time column, log_id set to None for all rows")

    # ------------------------------------------------------------------
    # Corrective Activity Tracking for AE Parameters (Dynamic Detection)
    # ------------------------------------------------------------------
    # Use the same dynamic detection for corrective activity tracking
    # This ensures consistency with log tracking for all machines
    corrective_params = log_tracking_params
    LOGGER.info(f"Corrective activity tracking parameters: {corrective_params}")

    # Use machine_data_list DataFrame for corrective activity tracking
    df_recent_data = machine_data_list.copy()
    df_recent_data["updatedate"] = df_recent_data["time"]

    # Filter for the specific parameters
    df_corrective_params = df_recent_data[df_recent_data["machine_parameters_id"].isin(corrective_params)].copy()

    if not df_corrective_params.empty:
        LOGGER.info(f"Found data for corrective parameters: {df_corrective_params['machine_parameters_id'].unique()}")

        # Step 2: Filter for abnormal data (condition > 1)
        df_abnormal_data = df_corrective_params[df_corrective_params["condition"] > 1].copy()

        if not df_abnormal_data.empty:
            LOGGER.info(f"Found {len(df_abnormal_data)} abnormal data points for corrective parameters")

            # Rename columns to match expected format
            df_abnormal_data.rename(columns={"machine_parameters_id": "signalname"}, inplace=True)

            # Step 3: Check Activity - Distinguishing New vs Existing
            # Get unique parameter IDs from abnormal data
            parameter_ids = df_abnormal_data['signalname'].unique().tolist()

            # Create unique combinations of (parameter_id, condition_id)
            unique_combinations = (df_abnormal_data[['signalname', 'condition']].
                                   drop_duplicates().apply(tuple, axis=1).tolist())

            # Query database to find existing activities matching these combinations
            existing_ids = select_activities_by_machine_params_condition(unique_combinations)

            # Separate new vs existing
            existing_ids_set = set(existing_ids)
            new_combinations = [combo for combo in unique_combinations if combo not in existing_ids_set]
            existing_combinations = [combo for combo in unique_combinations if combo in existing_ids_set]

            new_ids = [combo[0] for combo in new_combinations]
            existing_ids_list = [combo[0] for combo in existing_combinations]

            # Filter data accordingly
            df_new_activity = None
            df_existing_activity = None

            if new_ids:
                df_new_activity = df_abnormal_data[df_abnormal_data['signalname'].isin(new_ids)]
                LOGGER.info(f"Found {len(df_new_activity)} new activity records")

            if existing_ids_list:
                df_existing_activity = df_abnormal_data[df_abnormal_data['signalname'].isin(existing_ids_list)]
                LOGGER.info(f"Found {len(df_existing_activity)} existing activity records")

            # Step 4: Insert New Activity
            if df_new_activity is not None and not df_new_activity.empty:
                # Prepare record with required columns
                record_new = df_new_activity.loc[:, ["signalname", "updatedate", "condition", "value"]].copy()
                record_new["latest_occurrence"] = record_new["updatedate"]  # Same as initial time
                record_new['number_of_occurrences'] = 1  # First occurrence

                # Convert to list of tuples for insertion
                record_list_new = record_new.values.tolist()

                table_name = "corrective_activity"
                table_column_names = ("machine_parameters_id", "date_of_identification",
                                      "parameter_condition_id", "recent_value",
                                      "latest_occurrence", "number_of_occurrences")

                from app.database.crud_operations import insert_new_data_bulk_timescaledb
                insert_new_data_bulk_timescaledb(records=record_list_new, table_name=table_name,
                                                 table_column_names=table_column_names, db_schema="tiei_sample_4")
                LOGGER.info(f"Inserted {len(record_list_new)} new corrective activity records")

            # Step 5: Update Existing Activity
            if df_existing_activity is not None and not df_existing_activity.empty:
                update_corrective_activities_from_dataframe(df_existing_activity)
                LOGGER.info(f"Updated {len(df_existing_activity)} existing corrective activity records")

    # Reorder columns to include log_id before converting to list
    # Note: real_time_machine_parameters table has columns: time, machine_parameters_id, value, log_id
    # condition column is NOT included in this table
    machine_data_list = machine_data_list[["time", "machine_parameters_id", "value", "log_id"]]

    LOGGER.info(f"DEBUG: Before NaN replacement - machine_data_list shape: {machine_data_list.shape}")
    LOGGER.info(f"DEBUG: Before NaN replacement - log_id column sample:\n{machine_data_list['log_id'].head(10)}")

    # Convert to numpy list for database insertion
    # Replace NaN with None to ensure database compatibility
    machine_data_list = machine_data_list.where(pd.notna(machine_data_list), None)

    LOGGER.info(f"DEBUG: After NaN replacement - log_id column sample:\n{machine_data_list['log_id'].head(10)}")

    # Convert to list and ensure proper types for pgcopy
    records = []
    conversion_errors = 0
    for idx, row in enumerate(machine_data_list.itertuples(index=False)):
        try:
            # Convert to list and handle None values properly
            record = [
                row[0],  # time
                int(row[1]) if pd.notna(row[1]) else None,  # machine_parameters_id
                float(row[2]) if pd.notna(row[2]) else None,  # value
                int(row[3]) if pd.notna(row[3]) else None  # log_id
            ]
            records.append(record)

            # Log first few records for debugging
            if idx < 5:
                LOGGER.info(f"DEBUG: Record {idx} - time={record[0]}, param_id={record[1]}, value={record[2]}, log_id={record[3]}, types={[type(x).__name__ for x in record]}")

        except Exception as e:
            conversion_errors += 1
            LOGGER.error(f"DEBUG: Conversion error at row {idx}: {e}, row data: {row}")

    LOGGER.info(f"DEBUG: Total records converted: {len(records)}, Conversion errors: {conversion_errors}")
    LOGGER.info(f"DEBUG: Sample of first 3 converted records: {records[:3]}")

    return records, machine_data_active_list, next_alert_time_for_all_signals


def check_for_new_anomaly(current_anomaly, next_alert_time_for_all_signals):
    try:

        current_anomaly = current_anomaly.assign(next_alert_time=current_anomaly['machine_parameters_id'])
	#current_anomaly["next_alert_time"] = current_anomaly["machine_parameters_id"]
        current_anomaly['next_alert_time'] = current_anomaly['machine_parameters_id']. \
            map(next_alert_time_for_all_signals)
        LOGGER.debug(current_anomaly.head())

        # Getting only the data which was already existing in the "next_alert_time_for_all_signals" attribute
        # By filtering only non null values, since the above mapping will result in null values if the value is not
        # found in the keys of the given dictionary
        existing_new_alerts = current_anomaly[current_anomaly['next_alert_time'].notnull()]

        # Only if there is any new alerts for existing signals, we do the following
        if not existing_new_alerts.empty:

            # We first filter out only those rows that have latest update time greater than the next_alert_time
            existing_new_alerts = existing_new_alerts[
                (existing_new_alerts["time"] > existing_new_alerts["next_alert_time"])]

            # We do the following only if after filter, there is some new data
            if not existing_new_alerts.empty:
                # Saving the new time for next alerts for existing signals
                next_alert_time_df = existing_new_alerts.copy(deep=True)

                # We set the next alert time to the current "updatedate" time + 8 hours (the grace period we give
                # Until the same parameter needs to be reported when it is not in OK condition)
                next_alert_time_df["next_alert_time"] = next_alert_time_df["time"] + \
                                                        pd.to_timedelta(4, unit='h')

                if "warning_limit" in next_alert_time_df.columns:
                    # Dropping unwanted columns
                    next_alert_time_df = next_alert_time_df.drop(columns=["time", "value", "condition",
                                                                          "parameter_name", "warning_limit",
                                                                          "critical_limit"])
                else:
                    # Dropping unwanted columns
                    next_alert_time_df = next_alert_time_df.drop(columns=["time", "value",
                                                                          "condition", "parameter_name"])

                # Converting the dataframe to dictionary, whose key are the signal name (id) and values
                # Are the latest updatedate plus 4 hours
                next_alert_time_dict = next_alert_time_df.set_index("machine_parameters_id").T.to_dict("list")

                # The above dictionary will have the next alert time in a list, so in the below code
                # We remove the time by accessing the list
                next_alert_time_dict = {parameters_id: next_alert_time[0] for parameters_id, next_alert_time
                                        in next_alert_time_dict.items()}

                # Updating the old dictionary that stores the "next_alert_time_for_all_signals" with the new time
                # Generated from the new signals that were not in OK condition
                next_alert_time_for_all_signals.update(next_alert_time_dict)
                LOGGER.debug("NEW ALERTS EXISTING DICTIONARY")
                LOGGER.debug(next_alert_time_for_all_signals)

        # All the data that were not filtered out previously fall under the category of new alerts
        # Meaning this signal was never in warning/critical condition and was not previously stored
        # In current_anomaly.next_alert_time_for_all_signals dictionary
        new_alerts_new = current_anomaly[current_anomaly['next_alert_time'].isnull()]
        LOGGER.debug("NEW ALERTS")
        LOGGER.debug(new_alerts_new.head())

        # Only if there is any new alerts for new signals(that were not previously stored), we do the following
        if not new_alerts_new.empty:
            # Saving the new time for next alerts for new signals
            next_alert_time_df = new_alerts_new.copy(deep=True)

            # We set the next alert time to the current "updatedate" time + 4 hours (the grace period we give
            # Until the same parameter needs to be reported when it is not in OK condition)
            next_alert_time_df["next_alert_time"] = next_alert_time_df["time"] + pd.to_timedelta(4, unit='h')
            print(next_alert_time_df.columns)
            if "warning_limit" in next_alert_time_df.columns:
                # Dropping unwanted columns
                next_alert_time_df = next_alert_time_df.drop(
                    columns=["time", "value", "condition", "parameter_name", "warning_limit",
                             "critical_limit"])
            else:
                # Dropping unwanted columns
                next_alert_time_df = next_alert_time_df.drop(
                    columns=["time", "value", "condition", "parameter_name"])

            # Converting the dataframe to dictionary, whose key are the signal name (id) and values
            # Are the latest updatedate plus 8 hours
            # This will raise an issue, because the program history might have more than two cycle's data
            # That needs to be checked and added, but in that case, the same signal id will be having condition
            # Value equal to 2 or 3 (corresponding to the two or more cycles), in that case some index will be
            # omitted directly by pandas, currently this is fine, if any issue occurs change the logic
            next_alert_time_dict = next_alert_time_df.set_index("machine_parameters_id").T.to_dict("list")

            # The above dictionary will have the next alert time in a list, so in the below code
            # We remove the time by accessing the list
            next_alert_time_dict = {parameters_id: next_alert_time[0] for parameters_id, next_alert_time in
                                    next_alert_time_dict.items()}

            # Updating the old dictionary that stores the "next_alert_time_for_all_signals" with the new time
            # Generated from the new signals that were not in OK condition
            next_alert_time_for_all_signals.update(next_alert_time_dict)
            LOGGER.debug("NEW ALERTS DICTIONARY")
            LOGGER.debug(next_alert_time_for_all_signals)

        # The following code will be executed only if any one (or both) of alerts (existing signals or new signals)
        # is not empty
        if (not existing_new_alerts.empty) or (not new_alerts_new.empty):

            # We set the new alerts to be union of two alert data
            new_alerts_combined = pd.concat([existing_new_alerts.drop(columns=["machine_parameters_id",
                                                                               "next_alert_time"]),
                                             new_alerts_new.drop(columns=["machine_parameters_id",
                                                                          "next_alert_time"])])
            print("OKOKOK")

            new_alerts_combined["Parameter"] = new_alerts_combined["parameter_name"]

            condition_mapping = {2: "Warning", 3: "Critical", 1: "Normal"}

            new_alerts_combined['Status'] = new_alerts_combined['condition']. \
                map(condition_mapping)

            new_alerts_combined = new_alerts_combined.drop(columns=["condition", "parameter_name"])

            if "warning_limit" in new_alerts_combined.columns:
                new_alerts_combined = new_alerts_combined[["time", "Parameter", "value", "Status",
                                                           "warning_limit", "critical_limit"]]
            else:
                new_alerts_combined = new_alerts_combined[["time", "Parameter", "Status"]]

            new_alerts_combined.insert(0, 'S.No', range(1, 1 + len(new_alerts_combined)))
            new_alerts_combined['time'] = new_alerts_combined['time'].astype(str)
            print("anomaly_ok_1")
            return new_alerts_combined, next_alert_time_for_all_signals

        else:
            # If both alerts are empty, we set the new alerts to None
            print("anomaly_ok_2")
            return None, None
    except Exception as error:
        LOGGER.exception(f"Error while checking for new anomaly: {error}")


def main():
    """
    Main Function
    ====================
    
    Main function to call appropriate functions to test out the transformation functions

    """
    # LOGGER.setLevel("INFO")
    # extract_static_data(Path(MONITORING_DIRECTORY) / Path("A_220429_084923_3611242204282547_LOG_11_989F.csv"))
    #transform_log_files(Path(MONITORING_DIRECTORY) / Path("A_220429_083650_3611242204282543_LOG_07_989F.csv"))
    transform_log_files_laser_active(Path(MONITORING_DIRECTORY) / Path("A_220429_083650_3611242204282543_LOG_07_989F"
                                                                       ".csv"))

    #transform_log_files_spm_2_active(Path(MONITORING_DIRECTORY_2) / Path("JOP105.CSV"), machine_id=61)


if __name__ == '__main__':
    main()
