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
    * insert_new_data_bulk_timescaledb - Function that connects to mongodb by creating a
                                            client at the start of the application.
    * insert_new_data_timescaledb - Function that destroys the connection to mongodb by closing the mongodb client.
    * read_data_timescaledb - Function that destroys the connection to mongodb by closing the mongodb client.
"""

# Standard library imports
import logging
import pprint
import datetime

# Related third party imports
import psycopg2
from pgcopy import CopyManager
from psycopg2 import OperationalError
from psycopg2.extras import execute_batch

# Local application/library specific imports
from collector_app.database import TIMESCALEDB_URL
from collector_app.exception_helper.custom_exception_classes import TimescaleDbConnectionFailure

__author__ = "smt18m005@iiitdm.ac.in"

LOGGER = logging.getLogger(__name__)


def insert_new_data_bulk_timescaledb(records, table_name="real_time_machine_parameters",
                                     table_column_names=('time', 'machine_parameters_id', 'value'),
                                     db_schema="tiei_sample_4"):
    """

    Insert New Data Bulk TimescaleDB
    ====================================

    Function used to insert new bulk data into timescaledb

    :param records: list of new rows to be added
    :type records: list

    :param db_schema: The schema where the data has to inserted in timescaledb
    :type db_schema: str

    :param table_name: The table where the new data has to be inserted in timescaledb
    :type table_name: str

    :param table_column_names: The tuple of column names for which the data will be populated
    :type table_column_names: tuple

    :return: Nothing
    :rtype: None

    """

    try:

        with psycopg2.connect(TIMESCALEDB_URL) as connection:

            # connection_cursor = connection.cursor()
            # connection_cursor.execute("SET TIME ZONE 'Asia/Calcutta'")
            # connection.commit()
            # The table column name, whose value we will be inserting ( excluding id and condition for now)

            mgr = CopyManager(connection, f'{db_schema}.' + table_name, table_column_names)

            mgr.copy(records)

            connection.commit()

    except OperationalError as error:
        LOGGER.exception(f"Error while connecting to TimescaleDB: {error}")
        raise TimescaleDbConnectionFailure(error)
    except ValueError as error:
        LOGGER.exception(f"Error while connecting to TimescaleDB using pgcopy: {error}")
        raise TimescaleDbConnectionFailure(error)
    except Exception as error:
        LOGGER.exception(f"Error while connecting to TimescaleDB: {error}")
        raise TimescaleDbConnectionFailure(error)


def update_data_bulk_timescaledb(records, table_name="real_time_machine_parameters_active",
                                 db_schema="tiei_sample_4"):
    """

    Update Data Bulk TimescaleDB
    ====================================

    Function used to update multiple data in a single transaction (or batch of transaction).
    This is specifically used to update the real time machine parameters active table in the database

    :param records: tuple of dictionary
    :type records: tuple[dict]

    :param db_schema: The schema where the data has to inserted in timescaledb
    :type db_schema: str

    :param table_name: The table where the new data has to be inserted in timescaledb
    :type table_name: str

    :return: Nothing
    :rtype: None

    """

    try:

        with psycopg2.connect(TIMESCALEDB_URL) as connection:

            db_cursor = connection.cursor()

            full_table_name = db_schema + "." + table_name

            sql_statement_for_prepare = f"PREPARE updateStmt AS UPDATE {full_table_name} SET time=$1," \
                                        " value=$2, condition_id=$3 WHERE machine_parameters_id=$4"

            db_cursor.execute(sql_statement_for_prepare)

            sql_statement_for_batch_update = "EXECUTE updateStmt (%(time)s, %(value)s," \
                                             " %(condition_id)s, %(machine_parameters_id)s)"
            page_size = 100
            execute_batch(db_cursor, sql_statement_for_batch_update, records, page_size=page_size)
            db_cursor.execute("DEALLOCATE updateStmt")

            connection.commit()

    except OperationalError as error:
        LOGGER.exception(f"Error while connecting to TimescaleDB: {error}")
        raise TimescaleDbConnectionFailure(error)
    except ValueError as error:
        LOGGER.exception(f"Error while connecting to TimescaleDB using pgcopy: {error}")
        raise TimescaleDbConnectionFailure(error)
    except Exception as error:
        LOGGER.exception(f"Error while connecting to TimescaleDB: {error}")
        raise TimescaleDbConnectionFailure(error)


def insert_new_data_timescaledb(records, table_column_names, table_name="real_time_machine_parameters",
                                db_schema="tiei_sample_4"):
    """
    Insert New Data
    =============================

    Function used to insert new data into timescaledb

    :param records: list of new rows to be added
    :type records: list

    :param db_schema: The schema where the data has to inserted in timescaledb
    :type db_schema: str

    :param table_name: The table where the new data has to be inserted in timescaledb
    :type table_name: str

    :param table_column_names: The tuple of column names for which the data will be populated
    :type table_column_names: tuple

    :return: Return the inserted id
    :rtype: int

    """

    try:
        with psycopg2.connect(TIMESCALEDB_URL) as connection:

            connection_cursor = connection.cursor()
            column_name = ""
            value_string = ""

            # Creating column name and value string to be used in the sql query template
            for c_name_index in range(len(table_column_names) - 1):
                column_name += table_column_names[c_name_index] + ", "
                value_string += "%s, "
            column_name += table_column_names[-1]
            value_string += "%s"

            sql_statement = f"INSERT INTO {db_schema}.{table_name} (" + column_name + ") VALUES (" + value_string + \
                            ") returning id;"

            LOGGER.debug(sql_statement)

            # connection_cursor.execute("SET TIME ZONE 'Asia/Calcutta'")
            connection_cursor.execute(sql_statement, records)
            inserted_id = connection_cursor.fetchone()[0]
            connection.commit()
            return inserted_id
    except OperationalError as error:
        LOGGER.exception(f"Error while connecting to TimescaleDB: {error}")
        raise TimescaleDbConnectionFailure(error)
    except Exception as error:
        LOGGER.exception(f"Error while connecting to TimescaleDB: {error}")
        raise TimescaleDbConnectionFailure(error)


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
    except OperationalError as error:
        LOGGER.exception(f"Error while connecting to TimescaleDB: {error}")
        raise TimescaleDbConnectionFailure(error)
    except Exception as error:
        LOGGER.exception(f"Error while connecting to TimescaleDB: {error}")
        raise TimescaleDbConnectionFailure(error)


def execute_update_query_timescaledb(query):
    """

    Execute any update query on the timescaledb
    ===============================================

    Function used to update data into timescaledb

    :param query: The sql (update) query that needs to be executed
    :type query: str

    :return: Nothing
    :rtype: None

    """
    try:

        with psycopg2.connect(TIMESCALEDB_URL) as connection:

            # The table column name, whose value we will be inserting ( excluding id and condition for now)

            connection_cursor = connection.cursor()

            # connection_cursor.execute("SET TIME ZONE 'Asia/Calcutta'")
            connection_cursor.execute(query)

            connection.commit()
    except OperationalError as error:
        LOGGER.exception(f"Error while connecting to TimescaleDB: {error}")
        raise TimescaleDbConnectionFailure(error)
    except Exception as error:
        LOGGER.exception(f"Error while connecting to TimescaleDB: {error}")
        raise TimescaleDbConnectionFailure(error)


def read_data_timescaledb(table_column_names, table_name="machines", db_schema="tiei_sample_4"):
    """

    Read New Data
    =============================

    Function used to read data from timescaledb

    :param db_schema: The schema where the data has to inserted in timescaledb
    :type db_schema: str

    :param table_name: The table where the new data has to be inserted in timescaledb
    :type table_name: str

    :param table_column_names: The list of column names for which the data will be read
    :type table_column_names: list

    :return: List of data
    :rtype: list

    """
    try:

        with psycopg2.connect(TIMESCALEDB_URL) as connection:

            # The table column name, whose value we will be inserting ( excluding id and condition for now)

            connection_cursor = connection.cursor()

            # Creating a string to be used in query that represents the columns to return
            column_name = ""
            for c_name_index in range(len(table_column_names) - 1):
                column_name += table_column_names[c_name_index] + ", "
            column_name += table_column_names[-1]

            sql_statement = f"SELECT " + column_name + f" FROM {db_schema}.{table_name} ;"

            LOGGER.debug(sql_statement)

            # connection_cursor.execute("SET TIME ZONE 'Asia/Calcutta'")
            connection_cursor.execute(sql_statement)
            records = connection_cursor.fetchall()

            connection.commit()
            return records
    except OperationalError as error:
        LOGGER.exception(f"Error while connecting to TimescaleDB: {error}")
        raise TimescaleDbConnectionFailure(error)
    except Exception as error:
        LOGGER.exception(f"Error while connecting to TimescaleDB: {error}")
        raise TimescaleDbConnectionFailure(error)


def main():
    """
    Main Function
    ====================

    Main function to call appropriate functions to carry out required task

    """

    LOGGER.setLevel("INFO")

    # data = read_data_timescaledb(table_column_names=["group_name", "mongodb_query", "latest_update_time",
    #                                                  "warning_limit", "critical_limit", "parameter_type"],
    #                              table_name="parameters_group")
    # # data = {key: value for key, value in data}
    # pprint.pprint(data)

    # putting a comma in the end to indicate that it is a tuple
    data = ({"time": datetime.datetime.now(), "value": 300, "condition_id": 2, "machine_parameters_id": 126},
            {"time": datetime.datetime.now(), "value": 300, "condition_id": 2, "machine_parameters_id": 31},
            {"time": datetime.datetime.now(), "value": 350, "condition_id": 1, "machine_parameters_id": 31})

    update_data_bulk_timescaledb(records=data)


if __name__ == '__main__':
    main()
