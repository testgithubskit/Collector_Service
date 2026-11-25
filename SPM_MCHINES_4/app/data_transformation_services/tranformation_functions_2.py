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
from app.database.crud_operations import get_machine_parameters

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

    command_to_ping = ["ping", "-c", "1", "10.82.126.72"]
    host_status = subprocess.call(command_to_ping)
    if host_status != 0:
        raise ConnectionError("Host 10.82.126.72 is unreachable, try again!")

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
    command_to_ping = ["ping", "-c", "1", "172.18.20.27"]
    host_status = subprocess.call(command_to_ping)

    if host_status != 0:
        raise ConnectionError("Host 172.18.20.27 is unreachable, try again!")

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
    command_to_ping = ["ping", "-c", "1", "10.82.126.72"]
    host_status = subprocess.call(command_to_ping)
    #
    if host_status != 0:
        raise ConnectionError("Host 10.82.126.72 is unreachable, try again!")
    #
    if not os.path.exists(directory):
        raise FileNotFoundError("Path does not exist, check if shared drive is mounted")

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

    # Reading the csv file as pandas dataframe, skipping the first 28 rows ( as they represent the static data)
    # Using the above declared parameters as the required columns
    machine_data = pd.read_csv(directory, skiprows=11, usecols=[i for i in range(1, 17)], encoding="latin1")

    print(machine_data.head())

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

    machine_data.columns = columns

    # Converting the wide table to narrow (long) table, so that it could be fit into the database schema
    # Instead of saving the data with time, parameter1, parameter2, etc (represent column name)
    # We save it as time, parameter name, value (hence there will be multiple copies of the same timestamp
    machine_data = pd.melt(frame=machine_data, id_vars=["time"],
                           var_name="machine_parameters_id", value_name="value")

    print("OK")

    print(machine_data.head())

    # Converting the machine data to numpy and then to list
    machine_data = machine_data.to_numpy().tolist()

    return machine_data


def main():
    """
    Main Function
    ====================
    
    Main function to call appropriate functions to test out the transformation functions

    """
    LOGGER.setLevel("INFO")
    #extract_static_data(Path(MONITORING_DIRECTORY) / Path("A_220429_084923_3611242204282547_LOG_11_989F.csv"))
    #transform_log_files(Path(MONITORING_DIRECTORY) / Path("A_220429_083650_3611242204282543_LOG_07_989F.csv"))

    transform_log_files_spm_2_grinder(Path(MONITORING_DIRECTORY_2) / Path("SPM_2.csv"), machine_id=60)


if __name__ == '__main__':
    main()
