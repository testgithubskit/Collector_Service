#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
DATABASE UTILITY FUNCTIONS
================================

Module that has utility functions for database operations

This script requires the following modules be installed in the python environment
    * logging - To perform logging operations.
    * motor - To perform database connection operation in asynchronous way.

This script contains the following function
    * connect_to_mongo - Function that connects to mongodb by creating a client at the start of the application.
    * close_mongo_connection - Function that destroys the connection to mongodb by closing the mongodb client.
"""

# Standard library imports
import logging

# Related third party imports

# Local application/library specific imports
from app.database.crud_operations import execute_read_query_timescaledb
from app.database.crud_operations import read_data_timescaledb

__author__ = "smt18m005@iiitdm.ac.in"

LOGGER = logging.getLogger(__name__)


def get_reference_signal(parameter_id):
    """

    Function used to get the program all program history that has enddatetime greater than search_time

    :param parameter_id: The id of the parameter (in timescaledb) for which the reference signal has to be returned
    :type parameter_id: int

    :return: The list containing the reference signal for the given parameter id
    :rtype: list | None

    """

    try:
        # Query to return the reference signal value for the given parameter
        query = f"""
                SELECT reference_signal
                FROM tiei_sample_4.machine_parameters
                WHERE id = {parameter_id};
                """

        reference_signal = execute_read_query_timescaledb(query)[0][0]

        if reference_signal:
            return reference_signal

        return None
    except Exception as e:
        LOGGER.exception("Error getting reference signal for parameter: %s", parameter_id)


def get_parameters_limits_timescaledb():
    """

    This function returns all parameters warning limits and critical limits and parameter name (from the
    "machine_parameters"  table) for all available parameters

    :return: A tuple of dictionary with parameter id as key and parameter's critical limit/ warning limit as value
    :rtype: tuple[dict]

    """

    try:
        table_name = "machine_parameters"
        data = read_data_timescaledb(table_column_names=["id", "warning_limit", "critical_limit"],
                                     table_name=table_name)
        data_warning = {parameter[0]: parameter[1] for parameter in data}
        data_critical = {parameter[0]: parameter[2] for parameter in data}

        # In this case the number of parameters will be less than what is actually there, because of the
        # Fact that we're storing it in dictionary and it will store only unique key values
        # Hence if for our requirement the parameter are not unique (Such as ALARM - signalname)
        # then we have to use a combination of machine name and parameter name
        # Since our requirement is such that (17 parameters from cnc machines) all signals are unique
        # we can simply use the current approach of single dictionary
        LOGGER.debug(len(data))
        return data_warning, data_critical

    except Exception as e:
        LOGGER.exception("Error while reading from database")


def get_parameters_name_id_timescaledb():
    """

    This function returns all parameters warning limits and critical limits and parameter name (from the
    "machine_parameters"  table) for all available parameters

    :return: A tuple of dictionary with parameter id as key and parameter's critical limit/ warning limit as value
    :rtype: tuple[dict]

    """

    try:
        table_name = "machine_parameters"
        data = read_data_timescaledb(table_column_names=["id", "name"],
                                     table_name=table_name)
        parameter_name = {parameter[0]: parameter[1] for parameter in data}

        # In this case the number of parameters will be less than what is actually there, because of the
        # Fact that we're storing it in dictionary and it will store only unique key values
        # Hence if for our requirement the parameter are not unique (Such as ALARM - signalname)
        # then we have to use a combination of machine name and parameter name
        # Since our requirement is such that (17 parameters from cnc machines) all signals are unique
        # we can simply use the current approach of single dictionary
        LOGGER.debug(len(data))
        return parameter_name

    except Exception as e:
        LOGGER.exception("Error while reading from database")