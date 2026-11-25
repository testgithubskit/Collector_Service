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
import subprocess

# Related third party imports
import numpy as np

# Local application/library specific imports
from app.database.crud_operations import update_last_creation_time_sqlite_db, \
    insert_new_data_bulk_timescaledb, insert_new_data_timescaledb
from app.data_transformation_services.tranformation_functions import transform_log_files, extract_static_data, \
    transform_log_files_spm_2_grinder
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
    command_to_ping = ["ping", "-c", "1", "10.82.126.72"]
    host_status = subprocess.call(command_to_ping)

    LOGGER.info("Testing connection to host")
    if host_status != 0:
        raise ConnectionError("Host 10.82.126.72 is unreachable, try again!")
    #
    if not os.path.exists(directory):
        raise FileNotFoundError("Path does not exist, check if shared drive is mounted")

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
                    LOGGER.info(f"New File Name: {new_file}")

                    # Getting and Inserting Real Time Machine Parameters
                    real_time_data,  end_time = transform_log_files(directory / new_file)
                    insert_new_data_bulk_timescaledb(real_time_data)
                    LOGGER.info(f"Inserted real time data")

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


def start_monitoring_spm(directory: Path, last_creation_time: float, machine_id: int, sql_db: str):
    """
    START MONITORING SPM
    =========================

    Function that starts monitoring the given directory and calls appropriate functions to transform log
    files and insert into database.

    :param directory: The directory that needs to be monitored
    :param last_creation_time: The time of creation of last inserted log file
    :param machine_id: The ID of the machine for which the monitor has to run

    :return: Nothing
    """

    while True:
        # The function needs to keep looping

        LOGGER.info("Sleeping for 5 sec....")
        time.sleep(5)
        LOGGER.info("Waking up....")

        # Checking for new files
        try:
            new_files = check_for_new_files(directory, last_creation_time)
            LOGGER.info("Checked for new files")
        except Exception as error:
            # If in case any error with reading file in the network, we skip the remaining code
            LOGGER.info("Error while checking for new files")
            LOGGER.error(error)
            continue

        if new_files:
            # If new files exist
            LOGGER.info("New Files Found")
            try:
                # For every new file found do the following
                for new_file in new_files:
                    LOGGER.info(f"New File Name: {new_file}")

                    # Getting and Inserting Real Time Machine Parameters
                    real_time_data = transform_log_files_spm_2_grinder(directory / new_file, machine_id=machine_id)
                    insert_new_data_bulk_timescaledb(real_time_data)
                    LOGGER.info(f"Inserted real time data")

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
                update_last_creation_time_sqlite_db(new_creation_time=last_creation_time, sql_url=sql_db)
            except Exception as error:
                LOGGER.error(error)
                LOGGER.error("Was not able to update local sqlite db to update the last creation time")


def main():
    """
    MAIN DIRECTORY MONITORING
    =============================

    Main function to call appropriate functions to test out monitoring function
    """

    #directory = Path("D:\\PS-CMTI\\Codes\\PycharmProjects\\TIEI Master\\test\\csv_files")
    directory_2 = Path("D:\\PS-CMTI\\Codes\\PycharmProjects\\TIEI Master\\Laser "
                       "Cladding\\laser_clad_main\\inputs\\sample_data")

    # Sample time in epoch format
    last_creation_date = 1630576130
    start_monitoring_spm(directory_2, last_creation_date, machine_id=60)


if __name__ == '__main__':
    main()
