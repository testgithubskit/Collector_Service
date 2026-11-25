#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
DATABASE CRUD FUNCTIONS
================================

Module that has utility functions for database operations

This script requires the following modules be installed in the python environment

    Standard Library
    =================

    * logging - To perform logging operations.
    * contextlib - To perform database connection operation in asynchronous way.
    * sqlite3 - To perform database connection operation in asynchronous way.

    Related 3rd Party Library
    =============================

    * psycopg2 - To perform database connection operation in asynchronous way.
    * pgcopy - To perform database connection operation in asynchronous way.

This script contains the following function
    * update_last_creation_time_sqlite_db - Function that connects to mongodb by creating a
                                            client at the start of the application.
    * insert_new_data_timescaledb - Function that destroys the connection to mongodb by closing the mongodb client.
"""

# Standard library imports
import logging
from contextlib import closing
import sqlite3

# Related third party imports
import psycopg2
from pgcopy import CopyManager

# Local application/library specific imports
from app.database import SQLITE3_URL, TIMESCALEDB_URL

__author__ = "smt18m005@iiitdm.ac.in"

LOGGER = logging.getLogger(__name__)


def update_last_creation_time_sqlite_db(new_creation_time: float, sql_url=SQLITE3_URL):
    """
    Update Last Creation Time
    =============================

    Function used to update the last time when a new file was created in the sqlite3 database

    :param sql_url:
    :type sql_url: str
    :param new_creation_time: The time of creation of new files
    :return: Nothing
    """

    sql_statement_for_update = f"UPDATE last_time SET time = ? WHERE id = ?"
    with closing(sqlite3.connect(sql_url)) as connection:
        with closing(connection.cursor()) as cursor:
            cursor.execute(sql_statement_for_update, (new_creation_time, 1))
            connection.commit()
    LOGGER.info("updated last file creation time in DB")


def read_last_creation_time(sql_url=SQLITE3_URL) -> float:
    """

    :return:
    :rtype:
    """
    sql_statement_for_data_selection = "SELECT time FROM last_time"

    LOGGER.info("Connecting to DB")

    try:
        with closing(sqlite3.connect(sql_url)) as connection:
            with closing(connection.cursor()) as cursor:
                last_creation_time = cursor.execute(sql_statement_for_data_selection).fetchall()[0][0]
        LOGGER.info(f"The last created time is: {last_creation_time}")
        return last_creation_time
    except Exception as error:
        LOGGER.error(error)


def insert_new_data_bulk_timescaledb(records: list, table_name: str = "real_time_machine_parameters",
                                     table_column_names= (
                                             'time', 'machine_parameters_id', 'value'),
                                     db_schema: str = "tiei_sample_4"):
    """
    Insert New Data
    =============================

    Function used to insert new data into timescaledb

    :param db_schema:
    :type db_schema:
    :param table_name:
    :type table_name:
    :param table_column_names:
    :type table_column_names:
    :param records: list of new rows to be added
    :return: Nothing
    """
    try:

        with psycopg2.connect(TIMESCALEDB_URL) as connection:

            connection_cursor = connection.cursor()
            #connection_cursor.execute("SET TIME ZONE 'Asia/Calcutta'")
            #connection.commit()
            # The table column name, whose value we will be inserting ( excluding id and condition for now)

            mgr = CopyManager(connection, f'{db_schema}.' + table_name, table_column_names)

            mgr.copy(records)

            connection.commit()
    except Exception as error:
        LOGGER.error(f"Database Error: {error}")
        raise Exception("DB error")


def insert_new_data_timescaledb(records: list, table_column_names: list,
                                table_name: str = "real_time_machine_parameters",
                                db_schema: str = "tiei_sample_4"):
    """
    Insert New Data
    =============================

    Function used to insert new data into timescaledb

    :param db_schema:
    :type db_schema:
    :param table_name:
    :type table_name:
    :param table_column_names:
    :type table_column_names:
    :param records: list of new row to be added
    :return: Nothing
    """
    try:
        with psycopg2.connect(TIMESCALEDB_URL) as connection:

            # The table column name, whose value we will be inserting ( excluding id and condition for now)

            connection_cursor = connection.cursor()
            column_name = ""
            value_string = ""
            for c_name_index in range(len(table_column_names) - 1):
                column_name += table_column_names[c_name_index] + ", "
                value_string += "%s, "
            column_name += table_column_names[-1]
            value_string += "%s"

            sql_statement = f"INSERT INTO {db_schema}.{table_name} (" + column_name + ") VALUES (" + value_string + \
                            ") returning id;"

            LOGGER.debug(sql_statement)
            #connection_cursor.execute("SET TIME ZONE 'Asia/Calcutta'")
            connection_cursor.execute(sql_statement, records)
            inserted_id = connection_cursor.fetchone()[0]
            connection.commit()
            return inserted_id
    except Exception as error:
        LOGGER.error(f"Database Error: {error}")
        raise Exception("DB error")


def execute_read_query_timescaledb(query):

    """
    Execute any select query on the timescaledb
    ===============================================

    Function used to read data from timescaledb

    :param query: The sql (select) query that needs to be executed
    :type query: str

    :return: List of data
    :rtype: list
    """
    try:

        with psycopg2.connect(TIMESCALEDB_URL) as connection:

            # The table column name, whose value we will be inserting ( excluding id and condition for now)

            connection_cursor = connection.cursor()

            # connection_cursor.execute("SET TIME ZONE 'Asia/Calcutta'")
            connection_cursor.execute(query)
            records = connection_cursor.fetchall()

            connection.commit()
            return records
    except Exception as error:
        LOGGER.exception(f"Error while connecting to TimescaleDB: {error}")


def get_machine_parameters(machine_id=60):
    """

    Function used to get all parameters for a given machine id

    :param machine_id: The id of the machine for which the details are to be
    returned
    :type machine_id: int

    :return: The list containing the dynamic parameter configuration details for the given parameter id
    :rtype: list | None

    """

    try:
        # Query to return the reference signal value for the given parameter
        query = f"""
                SELECT id
                FROM tiei_sample_4.machine_parameters
                WHERE machine_id = {machine_id}
                ORDER BY id;
                """

        parameters_ids = execute_read_query_timescaledb(query)
        parameters_ids = [parameter[0] for parameter in parameters_ids]

        if parameters_ids:
            return parameters_ids
        return None
    except Exception as error:
        LOGGER.exception(f" Unknown Error While getting dynamic parameter from timescaledb: {error.args[0]}")


def main():
    """
    Main Function
    ====================

    Main function to call appropriate functions to

    """
    LOGGER.setLevel("INFO")

    # static_data_columns_production = ['machine_id', 'start_time', 'event_id']
    # static_data_record_production = [1, "2021-10-19 10:23:54+0530", 1]

    # static_data_columns_production = ['start_time', 'machine_id', 'part_number', 'event_id']
    # static_data_record_production = ["2021-10-19 10:23:54+0530", 1, "_3611242204282547", 2]
    #
    # insert_new_data_timescaledb(records=static_data_record_production,
    #                             table_name="machine_production_timeline",
    #                             table_column_names=static_data_columns_production)

    # real_time_data = [[2, 1, 900], [2, 2, 900]]
    # insert_new_data_bulk_timescaledb(real_time_data, table_name='event_static_machine_parameters',
    #                                  table_column_names=['event_id', 'parameter', 'value'])

    get_machine_parameters()


if __name__ == '__main__':
    main()
