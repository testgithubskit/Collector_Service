#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
MONITORING APPLICATION
================================

Module that contains required scripts to monitor directory for new files and insert data to database

This script requires the following modules be installed in the python environment

    Standard Library
    =================

    * logging - To perform logging operations
    * pathlib - To work with files and directories
    * os      - To interact with the os
    * time    - To work with time objects

    Related 3rd Party Library
    =============================

    * numpy - To work with arrays

This script contains the following function
    * check_for_new_files - Function used to check if new files have been created in the given directory
    since the last time a new file was created
    * start_monitoring - main function to call appropriate functions to run the monitoring functions
    * main - Main function to call appropriate functions to test out monitoring function
"""

# Standard library imports
import logging
from pathlib import Path
import os
import time
import datetime
from app.utils import INPUT_ARGUMENTS
from app.database.crud_operations import insert_update_time_machine

# Related third party imports
import numpy as np

# Local application/library specific imports
from app.database.crud_operations import update_last_creation_time_sqlite_db, \
    insert_new_data_bulk_timescaledb, insert_new_data_timescaledb, update_data_bulk_timescaledb
from app.data_transformation_services.tranformation_functions import transform_log_files, extract_static_data, \
    transform_log_files_spm_2_grinder, transform_log_files_spm_2_active, transform_log_files_laser_active

from app.database import SQLITE3_URL_2

__author__ = "smt18m005@iiitdm.ac.in"

LOGGER = logging.getLogger(__name__)


def check_for_new_files(directory: Path, last_creation_time: float) -> list:
    """
    Check For New Files
    =======================

    Function used to check if new files have been created in the given directory since the last time a new file was
    created.

    :param directory: The directory in which we want to check for new files
    :param last_creation_time: The last time (time since epoch) a new file(s) was created in the given directory
    :return: return the list (iterable) of newly created files
    """

    # command_to_ping = ["ping", "-c", "1", "172.18.20.27"]
    # host_status = subprocess.call(command_to_ping)
    # if host_status != 0:
    #     raise ConnectionError("Host 172.18.20.27 is unreachable, try again!")
    #
    # if not os.path.exists(directory):
    #     raise FileNotFoundError("Path does not exist, check if shared drive is mounted")

    # Getting all the file names in the given directory
    files_in_directory = os.listdir(directory)

    # Filtering out the files, only the files which was created after the last creation time will be selected below
    new_files = filter(lambda current_file: os.path.getctime(directory / current_file) > last_creation_time,
                       files_in_directory)

    return list(new_files)


def start_monitoring(directory: Path, last_creation_time: float):
    """
    START MONITORING
    ====================

    Function that starts monitoring the given directory and calls appropriate functions to transform log
    files and insert into database.

    :param directory: The directory that needs to be monitored
    :param last_creation_time: The time of creation of last inserted log file
    :return: Nothing
    """

    next_alert_time_for_all_signals = {}

    while True:
        # The function needs to keep looping

        LOGGER.info("Sleeping for 5 sec....")
        time.sleep(5)
        LOGGER.info("Waking up....")

        # Checking for new files
        try:
            new_files = check_for_new_files(directory, last_creation_time)
        except Exception as error:
            # If in case any error with reading file in the network, we skip the remaining code
            LOGGER.error(error)
            continue

        if new_files:
            # If new files exist
            LOGGER.info("New Files Found")
            try:
                # For every new file found do the following
                for new_file in new_files:
                    LOGGER.inf(f"The c time for {new_file} is {os.path.getctime(directory / new_file)}")

                    # Getting and Inserting Real Time Machine Parameters
                    # real_time_data, end_time = transform_log_files(directory / new_file)
                    real_time_data, end_time, real_time_data_active, next_alarm_time_updated = \
                        transform_log_files_laser_active(directory=directory / new_file,
                                                         next_alert_time_for_all_signals=
                                                         next_alert_time_for_all_signals)

                    next_alert_time_for_all_signals = next_alarm_time_updated

                    insert_new_data_bulk_timescaledb(real_time_data, table_column_names=(
                        'time', 'machine_parameters_id', 'value', 'condition_id'))
                    LOGGER.info(f"Inserted real time data")

                    active_records_tuple = tuple({"time": record_data[0], "machine_parameters_id": record_data[1],
                                                  "value": record_data[2], "condition_id": record_data[3]}
                                                 for record_data in real_time_data_active)

                    update_data_bulk_timescaledb(active_records_tuple)
                    LOGGER.info(f"Updated real time data active")

                    # Getting and Inserting Machine Event Timeline
                    static_data = extract_static_data(directory / new_file)
                    static_data_columns_event = ['machine_id', 'start_time', 'end_time', 'events_id']

                    static_data_record_event = [1, str(static_data["time"]), str(end_time), 1]
                    event_id = insert_new_data_timescaledb(records=static_data_record_event,
                                                           table_name="machine_event_timeline",
                                                           table_column_names=static_data_columns_event)
                    LOGGER.info(f"Inserted New Machine Event with id: {event_id}")

                    # Inserting Machine Production Timeline
                    static_data_columns_production = ['start_time', 'end_time', 'machine_id', 'part_number',
                                                      'machine_event_timeline_id']
                    static_data_record_production = [str(static_data["time"]), str(end_time), 1,
                                                     static_data["part_number"], event_id]

                    insert_new_data_timescaledb(records=static_data_record_production,
                                                table_name="machine_production_timeline",
                                                table_column_names=static_data_columns_production)

                    LOGGER.info(f"Inserted New Machine Production Timeline with part number: "
                                f"{static_data['part_number']}")

                    # Inserting Event Static Machine Parameters
                    static_param_data = []
                    for key, value in static_data.items():
                        # This table does not include time and part_number, hence excluding them
                        if key != "time" and key != "part_number":
                            static_param_data.append([event_id, key, float(value)])

                    insert_new_data_bulk_timescaledb(static_param_data, table_name='event_static_machine_parameters',
                                                     table_column_names=['machine_event_timeline_id',
                                                                         'machine_parameters_id',
                                                                         'value'])
                    LOGGER.info(f"Inserted event static machine parameters")
            except Exception as error:
                # If in case any error with database operations, such as connectivity error
                # Updating the local sqlite db for new creation time will be skipped
                LOGGER.error(error)
                continue

            # If more than one new file is available, the latest (maximum time) is chosen as the new last creation time
            last_creation_time = max([os.path.getctime(directory / current_file) for current_file in new_files])

            LOGGER.info(f"Latest Creation time: {last_creation_time}")
            try:
                # Updating the local sqlite db for the new last creation time
                update_last_creation_time_sqlite_db(last_creation_time)
            except Exception as error:
                LOGGER.error(error)
                LOGGER.error("Was not able to update local sqlite db to update the last creation time")


def start_monitoring_spm(directory: Path, machine_id: int,
                         file_counter: int = 50, date_str: str = None):
    """
    START MONITORING SPM
    =========================

    Monitors *directory* for log files and inserts processed data into the
    TimescaleDB (PostgreSQL) tables.  Progress is tracked exclusively via the
    ``machines.latest_time`` column in Postgres — no local SQLite database is
    used.

    Startup logic
    -------------
    1. Query ``machines.latest_time`` for *machine_id*.
       - If a value exists  → resume from that timestamp (files with ctime
         **strictly after** latest_time are candidates).
       - If NULL / no row   → use *date_str* (``--date`` CLI arg) as the
         starting boundary, and process the **very first** eligible file
         immediately on the first cycle.

    Counter logic
    -------------
    A running counter is maintained **across** loop cycles so that the Nth
    (= *file_counter*) file is always found even when files trickle in slowly.
    After each processing event the counter resets to 0 and ``start_ts`` is
    advanced to the processed file's ctime, so already-processed files are
    never re-evaluated.

    Data processing (transform → insert real_time → update active) is
    **unchanged** from the original implementation.

    :param directory: Directory to monitor (mapped from ``--directory``)
    :param machine_id: Machine primary key (``--machine_id``)
    :param file_counter: How many files to count before processing one
                         (``--file_counter``, default 50)
    :param date_str: ISO date string YYYY-MM-DD (``--date``); used only on
                     fresh start when machines.latest_time is NULL
    :return: Nothing – runs forever
    """

    from app.database.crud_operations import insert_update_time_machine, read_latest_time_machine

    next_alert_time_for_all_signals = {}

    # ------------------------------------------------------------------
    # Step 1: Determine the starting timestamp
    # ------------------------------------------------------------------
    latest_dt = read_latest_time_machine(machine_id)

    if latest_dt is not None:
        # Resume: machines table already has a checkpoint
        start_ts = latest_dt.timestamp()
        process_first_file = False
        LOGGER.info(f"Resuming from machines.latest_time={latest_dt} (machine_id={machine_id})")
    elif date_str:
        # Fresh start: use --date as the lower boundary
        try:
            date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d")
            start_ts = date_obj.timestamp()
        except Exception as e:
            LOGGER.error(f"Invalid --date format '{date_str}': {e}. Defaulting to epoch 0.")
            start_ts = 0.0
        process_first_file = True
        LOGGER.info(f"Fresh start from --date={date_str} (ts={start_ts})")
    else:
        start_ts = 0.0
        process_first_file = True
        LOGGER.warning("No --date provided and machines.latest_time is NULL. "
                       "Will process all files found in directory.")

    # Running counter persists across sleep cycles so we correctly count
    # files even when they arrive slowly over multiple iterations.
    running_counter = 0

    # ------------------------------------------------------------------
    # Step 2: Main monitoring loop
    # ------------------------------------------------------------------
    while True:
        LOGGER.info("Sleeping for 60 sec....")
        time.sleep(60)
        LOGGER.info("Waking up....")

        # --- Collect eligible files (ctime strictly after start_ts) ---
        try:
            all_files = os.listdir(directory)
        except Exception as error:
            LOGGER.error(f"Failed to list directory {directory}: {error}")
            continue

        eligible = []
        for f in all_files:
            try:
                ctime = os.path.getctime(directory / f)
                if ctime > start_ts:
                    eligible.append((ctime, f))
            except Exception as e:
                LOGGER.error(f"Error reading ctime for '{f}': {e}")

        # Sort ascending by creation time so we process in chronological order
        eligible.sort(key=lambda x: x[0])

        if not eligible:
            LOGGER.info("No new files found since last checkpoint.")
            continue

        LOGGER.info(f"{len(eligible)} eligible file(s) found since last checkpoint.")

        # --- Walk through eligible files and apply counter logic ---
        for file_ctime, new_file in eligible:
            running_counter += 1

            # Decide whether to process this file:
            #   • On a fresh start → process the very first file immediately
            #   • Subsequently     → process every file_counter-th file
            if process_first_file and running_counter == 1:
                should_process = True
            elif not process_first_file and running_counter >= file_counter:
                should_process = True
            else:
                should_process = False

            if not should_process:
                continue

            LOGGER.info(f"Processing file #{running_counter} (counter={file_counter}): {new_file}")

            try:
                # ---- Data transformation (unchanged) ----
                temp_data = transform_log_files_spm_2_active(
                    directory / new_file,
                    machine_id=machine_id,
                    next_alert_time_for_all_signals=next_alert_time_for_all_signals
                )

                if not temp_data:
                    LOGGER.warning(f"transform returned no data for '{new_file}', skipping.")
                    # Still advance bookmark so we don't re-count this file
                    start_ts = file_ctime
                    running_counter = 0
                    process_first_file = False
                    continue

                real_time_data, real_time_data_active, next_alarm_time_updated = temp_data
                next_alert_time_for_all_signals = next_alarm_time_updated

                # ---- Insert real-time machine parameters (with log_id) ----
                insert_new_data_bulk_timescaledb(
                    real_time_data,
                    table_name='real_time_machine_parameters',
                    table_column_names=('time', 'machine_parameters_id', 'value', 'log_id')
                )
                LOGGER.info("Inserted real time data")

                # ---- Update active table (unchanged) ----
                active_records_tuple = tuple(
                    {
                        "time": r[0],
                        "machine_parameters_id": r[1],
                        "value": r[2],
                        "condition_id": r[3]
                    }
                    for r in real_time_data_active
                )
                update_data_bulk_timescaledb(active_records_tuple)
                LOGGER.info("Updated real time data active")

                # ---- Update machines.latest_time (progress bookmark) ----
                processed_dt = datetime.datetime.fromtimestamp(file_ctime)
                insert_update_time_machine(machine_id, processed_dt)
                LOGGER.info(
                    f"Updated machines.latest_time={processed_dt} for machine_id={machine_id}"
                )

                # Advance checkpoint and reset counter for next cycle
                start_ts = file_ctime
                running_counter = 0
                process_first_file = False

            except Exception as error:
                LOGGER.error(f"Error processing '{new_file}': {error}")
                continue



def main():
    """
    MAIN DIRECTORY MONITORING
    =============================

    Main function to call appropriate functions to test out monitoring function
    """

    # directory = Path("D:\\PS-CMTI\\Codes\\PycharmProjects\\TIEI Master\\test\\csv_files")
    directory_2 = Path("D:\\PS-CMTI\\Codes\\PycharmProjects\\TIEI Master\\Laser "
                       "Cladding\\laser_clad_main\\inputs\\sample_data")

    # Sample time in epoch format
    last_creation_date = 1630576130
    start_monitoring_spm(directory_2, last_creation_date, machine_id=60)


if __name__ == '__main__':
    main()
