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
import datetime
from contextlib import closing
import sqlite3

# Related third party imports
import psycopg2
from pgcopy import CopyManager
from psycopg2.extras import execute_batch

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
                                     table_column_names=(
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
            # connection_cursor.execute("SET TIME ZONE 'Asia/Calcutta'")
            # connection.commit()
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
            # connection_cursor.execute("SET TIME ZONE 'Asia/Calcutta'")
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


def get_machine_parameters_type(machine_id=60, parameter_type="spm_static"):
    """

    Function used to get all parameters for a given machine id, of given parameter type (This is usually
    Used for spm machines)

    :param machine_id: The id of the machine for which the details are to be returned
    :type machine_id: int

    :param parameter_type: The parameter type
    :type parameter_type: str

    :return: The list containing the dynamic parameter configuration details for the given parameter id
    :rtype: list | None

    """

    try:
        # Query to return the reference signal value for the given parameter
        query = f"""
                SELECT id
                FROM tiei_sample_4.machine_parameters
                WHERE machine_id = {machine_id} AND parameter_type = '{parameter_type}'
                ORDER BY id;
                """

        parameters_ids = execute_read_query_timescaledb(query)
        parameters_ids = [parameter[0] for parameter in parameters_ids]

        if parameters_ids:
            return parameters_ids
        return None
    except Exception as error:
        LOGGER.exception(f" Unknown Error While getting dynamic parameter from timescaledb: {error.args[0]}")


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
    except Exception as e:
        LOGGER.exception("Error while reading from database")


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

            # Use INSERT ... ON CONFLICT UPDATE (UPSERT) to handle both new and existing parameters
            # This ensures new machines get their parameters inserted into the active table
            sql_statement_for_prepare = f"PREPARE upsertStmt AS INSERT INTO {full_table_name} " \
                                        "(time, machine_parameters_id, value, condition_id) " \
                                        "VALUES ($1, $4, $2, $3) " \
                                        "ON CONFLICT (machine_parameters_id) " \
                                        "DO UPDATE SET time=$1, value=$2, condition_id=$3"

            db_cursor.execute(sql_statement_for_prepare)

            sql_statement_for_batch_update = "EXECUTE upsertStmt (%(time)s, %(value)s," \
                                             " %(condition_id)s, %(machine_parameters_id)s)"
            page_size = 100
            execute_batch(db_cursor, sql_statement_for_batch_update, records, page_size=page_size)
            db_cursor.execute("DEALLOCATE upsertStmt")

            connection.commit()

    except Exception as e:
        LOGGER.exception("Error while reading from database")


def insert_update_time_machine(machine_id: int, latest_time: datetime.datetime,
                               db_schema: str = "tiei_sample_4"):
    """
    Insert / Update Latest Time In Machines Table
    =================================================

    Updates the ``latest_time`` column of the machines table for the given
    machine_id.  This is used by the SPM monitoring loop to record the
    creation-time of the last processed log file so that the container can
    resume from the correct position after a restart.

    :param machine_id: Primary key of the machine row to update
    :type machine_id: int

    :param latest_time: Creation-time of the last processed file
    :type latest_time: datetime.datetime

    :param db_schema: PostgreSQL schema name
    :type db_schema: str

    :return: Nothing
    """
    try:
        with psycopg2.connect(TIMESCALEDB_URL) as connection:
            cursor = connection.cursor()
            sql = f"UPDATE {db_schema}.machines SET latest_time = %s WHERE id = %s"
            cursor.execute(sql, (latest_time, machine_id))
            connection.commit()
            LOGGER.info(f"Updated machines.latest_time={latest_time} for machine_id={machine_id}")
    except Exception as error:
        LOGGER.error(f"Database Error (insert_update_time_machine): {error}")
        raise


def read_latest_time_machine(machine_id: int, db_schema: str = "tiei_sample_4"):
    """
    Read Latest Time From Machines Table
    ======================================

    Reads the ``latest_time`` column from the machines table for the given
    machine_id.  Returns ``None`` when the value is NULL or the row does not
    exist (i.e. fresh start).

    :param machine_id: Primary key of the machine row to query
    :type machine_id: int

    :param db_schema: PostgreSQL schema name
    :type db_schema: str

    :return: The stored datetime, or None
    :rtype: datetime.datetime | None
    """
    try:
        with psycopg2.connect(TIMESCALEDB_URL) as connection:
            cursor = connection.cursor()
            sql = f"SELECT latest_time FROM {db_schema}.machines WHERE id = %s"
            cursor.execute(sql, (machine_id,))
            row = cursor.fetchone()
            if row and row[0] is not None:
                LOGGER.info(f"Read machines.latest_time={row[0]} for machine_id={machine_id}")
                return row[0]  # psycopg2 returns Python datetime automatically
            LOGGER.info(f"No latest_time found for machine_id={machine_id} (fresh start)")
            return None
    except Exception as error:
        LOGGER.error(f"Database Error (read_latest_time_machine): {error}")
        return None


def select_activities_by_machine_params_condition(unique_combinations, db_schema: str = "tiei_sample_4"):
    """
    Select Activities By Machine Parameters and Condition
    ====================================================

    Query the corrective_activity table to find existing activities matching
    the given (machine_parameters_id, parameter_condition_id) combinations.

    :param unique_combinations: List of tuples (machine_parameters_id, parameter_condition_id)
    :type unique_combinations: list[tuple]

    :param db_schema: PostgreSQL schema name
    :type db_schema: str

    :return: List of existing (machine_parameters_id, parameter_condition_id) combinations
    :rtype: list[tuple]
    """
    try:
        if not unique_combinations:
            return []

        with psycopg2.connect(TIMESCALEDB_URL) as connection:
            cursor = connection.cursor()

            # Build the query to check for existing activities
            placeholders = ','.join(['(%s, %s)'] * len(unique_combinations))
            flat_params = [param for combo in unique_combinations for param in combo]

            query = f"""
                SELECT machine_parameters_id, parameter_condition_id
                FROM {db_schema}.corrective_activity
                WHERE (machine_parameters_id, parameter_condition_id) IN ({placeholders})
            """

            cursor.execute(query, flat_params)
            existing_combinations = cursor.fetchall()
            connection.commit()

            LOGGER.info(f"Found {len(existing_combinations)} existing corrective activities")
            return existing_combinations

    except Exception as error:
        LOGGER.error(f"Database Error (select_activities_by_machine_params_condition): {error}")
        raise


def update_corrective_activities_from_dataframe(df, db_schema: str = "tiei_sample_4"):
    """
    Update Corrective Activities From DataFrame
    ============================================

    Update existing corrective activity records with latest occurrence data.
    Updates: latest_occurrence, recent_value, number_of_occurrences
    Does NOT update: date_of_identification, parameter_condition_id

    :param df: DataFrame with columns: signalname, condition, updatedate, value
    :type df: pandas.DataFrame

    :param db_schema: PostgreSQL schema name
    :type db_schema: str

    :return: Nothing
    """
    try:
        with psycopg2.connect(TIMESCALEDB_URL) as connection:
            cursor = connection.cursor()

            for index, row in df.iterrows():
                machine_parameters_id = row["signalname"]
                condition_id = row["condition"]
                updatedate = row["updatedate"]
                value = row["value"]

                # Update the existing corrective activity record
                update_query = f"""
                    UPDATE {db_schema}.corrective_activity
                    SET latest_occurrence = %s,
                        recent_value = %s,
                        number_of_occurrences = number_of_occurrences + 1
                    WHERE machine_parameters_id = %s
                      AND parameter_condition_id = %s
                """

                cursor.execute(update_query, (updatedate, value, machine_parameters_id, condition_id))

            connection.commit()
            LOGGER.info(f"Updated {len(df)} corrective activity records")

    except Exception as error:
        LOGGER.error(f"Database Error (update_corrective_activities_from_dataframe): {error}")
        raise


def get_latest_log_id(db_schema: str = "tiei_sample_4"):
    """
    Get Latest Log ID from spm_log_files Table
    ===========================================

    Retrieves the maximum id from the spm_log_files table.
    Returns 0 if table is empty or doesn't exist.

    :param db_schema: PostgreSQL schema name
    :type db_schema: str

    :return: The latest log_id, or 0 if none exists
    :rtype: int
    """
    try:
        with psycopg2.connect(TIMESCALEDB_URL) as connection:
            cursor = connection.cursor()

            query = f"""
                SELECT COALESCE(MAX(id), 0)
                FROM {db_schema}.spm_log_files
            """

            cursor.execute(query)
            latest_id = cursor.fetchone()[0]
            connection.commit()

            LOGGER.info(f"Latest log_id from spm_log_files: {latest_id}")
            return latest_id

    except Exception as error:
        LOGGER.error(f"Database Error (get_latest_log_id): {error}")
        # Return 0 if table doesn't exist or other error
        return 0


def insert_spm_log_file(log_id: int, machine_parameter_id: int, time: datetime.datetime, rms: float = None,
                        db_schema: str = "tiei_sample_4"):
    """
    Insert Record into spm_log_files Table
    =======================================

    Inserts a new log file record with the given id, machine_parameter_id, time, and rms value.

    :param log_id: The unique log identifier
    :type log_id: int

    :param machine_parameter_id: The machine parameter id
    :type machine_parameter_id: int

    :param time: The timestamp (initial second of processing)
    :type time: datetime.datetime

    :param rms: The RMS value calculated from the 10-second data window
    :type rms: float

    :param db_schema: PostgreSQL schema name
    :type db_schema: str

    :return: Nothing
    """
    try:
        with psycopg2.connect(TIMESCALEDB_URL) as connection:
            cursor = connection.cursor()
            cursor.execute("SET TIME ZONE 'Asia/Calcutta'")
            connection.commit()

            query = f"""
                INSERT INTO {db_schema}.spm_log_files (id, machine_parameter_id, time, rms)
                VALUES (%s, %s, %s, %s)
            """

            cursor.execute(query, (log_id, machine_parameter_id, time, rms))
            connection.commit()

            LOGGER.info(f"Inserted spm_log_file record: id={log_id}, parameter_id={machine_parameter_id}, time={time}, rms={rms}")

    except Exception as error:
        LOGGER.error(f"Database Error (insert_spm_log_file): {error}")
        raise


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
