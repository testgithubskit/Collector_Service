#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
DATABASE UTILITY FUNCTIONS
================================

Module that has utility functions for database operations

This script requires the following modules be installed in the python environment

    Standard Library
    =================

    * logging - To perform logging operations.

    Related 3rd Party Library
    =============================

    * pymongo - To perform mongodb related operations.
    * pandas - To perform data manipulation and analysis operations

This script contains the following function
    * get_collector - Function that returns a client that communicates with the requested mongodb collection.
    * get_machine_parameters_count - This function returns the number of parameters for all machine.

    * get_machine_parameters_all - This function returns list of all parameters for requested machines.
    * get_machines_id_timescaledb - This function returns the machine id (from the "machines" table) for all
    available machines.

    * get_parameters_id_timescaledb - This function returns parameters id and parameter name (from the
    "machine_parameters" table) for all available.
    * insert_machines_from_mongo_to_timescale - Function that inserts all the machines available in mongodb into
     timescaledb.

    * get_machine_parameters_all_mongo - This function returns all machine parameters queried from mongodb.
    * insert_parameters_from_mongo_to_timescale - Function to insert all the parameters from mongodb to timescaledb.
    * main - Main function to call appropriate functions to carry out required task.

"""

# Standard library imports
import logging
import pprint
import re
from datetime import datetime, timezone

# Related third party imports
from pymongo import MongoClient
import pandas as pd
from pymongo.collection import Collection
from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure, NetworkTimeout, OperationFailure

# Local application/library specific imports
from collector_app.database import MONGODB_URL
from collector_app.database.crud_operations import insert_new_data_bulk_timescaledb, read_data_timescaledb, \
    execute_read_query_timescaledb, execute_update_query_timescaledb

from collector_app.exception_helper.custom_exception_classes import NoDataFromMongoDB, MongoDbConnectionFailure, \
    TimescaleDbConnectionFailure, MachineIdQueryFailure, ParameterIdQueryFailure, GetReferenceSignalFailure, \
    GetDynamicConfigFailure, SetDynamicConfigFailure

from collector_app.database import PARAMETER_CONFIG

__author__ = "smt18m005@iiitdm.ac.in"

LOGGER = logging.getLogger(__name__)

MONGO_CLIENT = MongoClient(MONGODB_URL)

MT_DATABASE = MONGO_CLIENT['MTLINKi']


def get_collector(collection="L1Signal_Pool_Active"):
    """

    Function that returns a client that communicates with the requested mongodb collection

    :param collection: The collection that the client wants to access
    :type collection: str

    :return: The collection class that allows communication with the required mongodb collection
    :rtype: Collection

    """

    return MT_DATABASE[collection]


def get_machine_parameters_count():
    """
    This function returns the number of parameters for all machine

    :return: A list of number of parameters for all machines
    :rtype: list

    """

    try:

        collector = get_collector("all_machine_paramters_view")

        pipeline = [
            {
                '$group': {
                    '_id': '$L1Name',
                    'parameters': {
                        '$sum': 1
                    }
                }
            }, {
                '$sort': {
                    '_id': 1
                }
            }
        ]

        data = collector.aggregate(pipeline)
        data = pd.DataFrame(list(data))

        data.columns = ["name", "parameters"]
        data['location'] = data.name.str[:3]

        data['location'] = data['location'].map({"T_C": "CRANK", "T_B": "BLOCK", "T_H": "HEAD"})

        data = data.to_numpy().tolist()

        return data
    except ServerSelectionTimeoutError as error:
        LOGGER.exception(f"Unable to select mongodb server with following error: {error.args}")
        raise MongoDbConnectionFailure("Error from 'get_machine_parameters_count'")
    except ConnectionFailure as error:
        LOGGER.exception(f"Unable to make connection to database server with following error: {error.args}")
        raise MongoDbConnectionFailure("Error from 'get_machine_parameters_count'")
    except NetworkTimeout as error:
        LOGGER.exception(f"Network timed out while connecting to database server with following error: {error.args}")
        raise MongoDbConnectionFailure("Error from 'get_machine_parameters_count'")
    except OperationFailure as error:
        LOGGER.exception(f"The database operation failed with following error: {error.args}")
        raise MongoDbConnectionFailure("Error from 'get_machine_parameters_count'")


def get_machine_parameters_all(machine_name):
    """

    This function returns list of all parameters for requested machines.

    :param machine_name: The machine for which all the parameters are needed
    :type machine_name: str

    :return: Returns a list of all parameters for the requested machine
    :rtype: list

    """

    try:

        collector = get_collector("all_machine_paramters_view")
        find_query = {'L1Name': machine_name}

        data = collector.find(find_query)
        data = list(data)

        return data
    except ServerSelectionTimeoutError as error:
        LOGGER.exception(f"Unable to select mongodb server with following error: {error.args[0]}")
        raise MongoDbConnectionFailure("Error from 'get_machine_parameters_all'")
    except ConnectionFailure as error:
        LOGGER.exception(f"Unable to make connection to database server with following error: {error.args[0]}")
        raise MongoDbConnectionFailure("Error from 'get_machine_parameters_all'")
    except NetworkTimeout as error:
        LOGGER.exception(f"Network timed out with following error: {error.args[0]}")
        raise MongoDbConnectionFailure("Error from 'get_machine_parameters_all'")
    except OperationFailure as error:
        LOGGER.exception(f"The database operation failed with following error: {error.args[0]}")
        raise MongoDbConnectionFailure("Error from 'get_machine_parameters_all'")


def get_machines_id_timescaledb():
    """

    This function returns the machine id (from the "machines" table) for all available machines

    :return: A dictionary with machine name as key and machine id as value
    :rtype: dict

    """

    try:
        table_name = "machines"
        data = read_data_timescaledb(table_column_names=["name", "id"], table_name=table_name)

        # Converting the list of tuple into dictionary
        data = {machine_name: machine_id for machine_name, machine_id in data}
        return data
    except TimescaleDbConnectionFailure as error:
        LOGGER.exception(f"Error While getting the machine's id from TimescaleDb {error.args[0]}")
        raise MachineIdQueryFailure("Error from 'get_machines_id_timescaledb'")
    except Exception as error:
        LOGGER.exception(f"Unknown error: {error.args[0]}")
        raise MachineIdQueryFailure("Error from 'get_machines_id_timescaledb'")


def get_parameters_id_timescaledb():
    """

    This function returns parameters id and parameter name (from the "machine_parameters" table) for all available
    parameters

    :return: A dictionary with parameter name as key and parameter id as value
    :rtype: dict

    """

    try:
        table_name = "machine_parameters"
        data = read_data_timescaledb(table_column_names=["name", "id"], table_name=table_name)
        data = {parameter_name: parameter_id for parameter_name, parameter_id in data}

        # In this case the number of parameters will be less than what is actually there, because of the
        # Fact that we're storing it in dictionary and it will store only unique key values
        # Hence if for our requirement the parameter are not unique (Such as ALARM - signalname)
        # then we have to use a combination of machine name and parameter name
        # Since our requirement is such that (19 parameters from cnc machines) all signals are unique
        # we can simply use the current approach of single dictionary
        LOGGER.debug(len(data))
        return data
    except TimescaleDbConnectionFailure as error:
        LOGGER.exception(f"Error While getting the machine's id from TimescaleDb {error.args[0]}")
        raise ParameterIdQueryFailure("Error from 'get_parameters_id_timescaledb'")
    except Exception as error:
        LOGGER.exception(f"Unknown error: {error.args[0]}")
        raise ParameterIdQueryFailure("Error from 'get_parameters_id_timescaledb'")


def get_parameters_limits_timescaledb():
    """

    This function returns all parameters warning limits and critical limits and parameter name (from the
    "machine_parameters"  table) for all available parameters

    :return: A tuple of dictionary with parameter name as key and parameter's critical limit/ warning limit as value
    :rtype: tuple[dict]

    """

    try:
        table_name = "machine_parameters"
        data = read_data_timescaledb(table_column_names=["name", "warning_limit", "critical_limit"],
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
    except TimescaleDbConnectionFailure as error:
        LOGGER.exception(f"Error While getting the machine's id from TimescaleDb {error.args[0]}")
        raise ParameterIdQueryFailure("Error from 'get_parameters_id_timescaledb'")
    except Exception as error:
        LOGGER.exception(f"Unknown error: {error.args[0]}")
        raise ParameterIdQueryFailure("Error from 'get_parameters_id_timescaledb'")


def insert_machines_from_mongo_to_timescale():
    """

    Function that inserts all the machines available in mongodb into timescaledb

    :return: Nothing
    :rtype: None

    """

    try:
        # This uses get_machine_parameters_count, which returns all machines, along with the count of available
        # Parameter for that machine
        records = get_machine_parameters_count()

        # Inserting the records
        insert_new_data_bulk_timescaledb(records, table_name="machines",
                                         table_column_names=('name', 'parameters', 'location'))
    except MongoDbConnectionFailure as error:
        LOGGER.exception(f"Error while getting the machine names from mongodb: {error.args[0]}")
    except Exception as error:
        LOGGER.exception(f"Unknown error while transferring machines data: {error.args[0]}")


def get_machine_parameters_all_mongo():
    """

    This function returns all machine parameters queried from mongodb

    :return: List of parameters for all machines
    :rtype: list

    """

    try:

        # Consist of dataframe of parameters for each machines aggregated
        parameters_data_frames = []

        machine_ids = get_machines_id_timescaledb()

        parameter_groups = get_parameter_group_config()

        # For all the machine name, id returned from the get_machines_id_timescaledb function do the following
        for machine_name, machine_id in machine_ids.items():

            # Getting all parameter for the current machine
            #machine_parameters = get_machine_parameters_all(machine_name)

            machine_parameters = []

            # The following code is used to add group parameter id (for the table tiei_sample_4.parameters_group)
            for group_id, regex_pattern, warning_limit, critical_limit, parameter_limit in parameter_groups:

                machine_parameters_group = get_param_mc_sig_mongo(machine_name=machine_name,
                                                                  signal_regex=regex_pattern)

                if not machine_parameters_group:
                    # If this machine is not available in MTLinki (Such as the SPM), then skip the remaining codes
                    continue

                for parameter_index in range(len(machine_parameters_group)):
                    machine_parameters_group[parameter_index]["parameter_group_id"] = group_id
                    machine_parameters_group[parameter_index]["warning_limit"] = warning_limit
                    machine_parameters_group[parameter_index]["critical_limit"] = critical_limit
                    machine_parameters_group[parameter_index]["parameter_type"] = parameter_limit

                machine_parameters.extend(machine_parameters_group)

            if not machine_parameters:
                # If in case the machine doesn't not have any parameters, then skip the remaining code
                continue

            # Consist of dataframe of parameters for current machine
            parameters_data_frame = pd.DataFrame(machine_parameters)

            # Adding a new column called machine_id equal to the current machine id
            parameters_data_frame["machine_id"] = machine_id

            # Initially, the unit is set to no unit (could be changed later)
            parameters_data_frame["unit_id"] = 6

            # Dropping unwanted columns
            parameters_data_frame = parameters_data_frame.drop(["L1Name"], axis=1)

            # Append the parameters for the current machine to the list consisting of parameter for all machines
            parameters_data_frames.append(parameters_data_frame)

        # Merging all the parameters
        all_parameters = pd.concat(parameters_data_frames)

        LOGGER.debug(all_parameters.head())

        data = all_parameters.to_numpy().tolist()

        return data
    except ServerSelectionTimeoutError as error:
        LOGGER.exception(f"Unable to select mongodb server with following error: {error.args[0]}")
    except ConnectionFailure as error:
        LOGGER.exception(f"Unable to make connection to database server with following error: {error.args[0]}")
    except NetworkTimeout as error:
        LOGGER.exception(f"Network timed out with following error: {error.args[0]}")
    except OperationFailure as error:
        LOGGER.exception(f"The database operation failed with following error: {error.args[0]}")


def get_param_mc_sig_mongo(machine_name="T_B_OP540", signal_regex="load(?i)"):
    """

    Function used to get the specific parameter group signal (using regex) for a given machine

    :param machine_name: The machine for which the number of parameters in the spindle and servo parameters group is
    required
    :type machine_name: str

    :param signal_regex: The regex that can filter out a specific parameter group
    :type signal_regex: str

    :return: The list of parameter for a given machine and parameter group
    :rtype: list

    """

    try:
        # Getting the mongodb client, that talks to L1Signal_Pool_Active
        collector = get_collector(collection="L1Signal_Pool_Active")

        # Getting the mongodb query parameter
        find_query = {"signalname": {'$regex': re.compile(rf"{signal_regex}")}, "L1Name": machine_name}

        # Projecting only required fields
        projection_fields = {"signalname": 1, "L1Name": 1, "_id": 0}

        # Getting the data
        data = collector.find(find_query, projection_fields)
        data = list(data)

        if data:
            return data

        return None

    except ServerSelectionTimeoutError as error:
        LOGGER.exception(f"Unable to select mongodb server with following error: {error.args[0]}")
        raise MongoDbConnectionFailure("Error from 'get_param_mc_sig_mongo'")
    except ConnectionFailure as error:
        LOGGER.exception(f"Unable to make connection to database server with following error: {error.args[0]}")
        raise MongoDbConnectionFailure("Error from 'get_param_mc_sig_mongo'")
    except NetworkTimeout as error:
        LOGGER.exception(f"Network timed out with following error: {error.args[0]}")
        raise MongoDbConnectionFailure("Error from 'get_param_mc_sig_mongo'")
    except OperationFailure as error:
        LOGGER.exception(f"The database operation failed with following error: {error.args[0]}")
        raise MongoDbConnectionFailure("Error from 'get_param_mc_sig_mongo'")


def get_spindle_servo_params_mongo(machine_name="T_B_OP540"):
    """

    Function used to get the total number of parameters in the spindle and servo parameters group, since these values
    change depending upon the number of axes available in the machine

    :param machine_name: The machine for which the number of parameters in the spindle and servo parameters group is
    required
    :type machine_name: str

    :return: The number of parameters
    :rtype: int | None

    """

    try:
        # Getting the mongodb client, that talks to L1Signal_Pool_Active
        collector = get_collector(collection="L1Signal_Pool_Active")

        # Getting the mongodb query parameter
        find_query = {"signalname": {'$regex': re.compile(r"load(?i)")}, "L1Name": machine_name}

        # Projecting only required fields
        projection_fields = {"signalname": 1, "updatedate": 1, "L1Name": 1, "value": 1, "_id": 0}

        # Getting the data
        data = collector.find(find_query, projection_fields).sort("updatedate", 1)
        data = list(data)

        if data:
            return len(data)

        return None

    except ServerSelectionTimeoutError as error:
        LOGGER.exception(f"Unable to select mongodb server with following error: {error.args[0]}")
        raise MongoDbConnectionFailure("Error from 'get_spindle_servo_params_mongo'")
    except ConnectionFailure as error:
        LOGGER.exception(f"Unable to make connection to database server with following error: {error.args[0]}")
        raise MongoDbConnectionFailure("Error from 'get_spindle_servo_params_mongo'")
    except NetworkTimeout as error:
        LOGGER.exception(f"Network timed out with following error: {error.args[0]}")
        raise MongoDbConnectionFailure("Error from 'get_spindle_servo_params_mongo'")
    except OperationFailure as error:
        LOGGER.exception(f"The database operation failed with following error: {error.args[0]}")
        raise MongoDbConnectionFailure("Error from 'get_spindle_servo_params_mongo'")


def get_program_history(search_time=datetime(2022, 3, 25, 10, 53, 0, tzinfo=timezone.utc)):
    """

    Function used to get the program all program history that has enddatetime greater than search_time

    :param search_time: The time after which program history will be searched for
    :type search_time: datetime

    :return: The list of program history
    :rtype: list | None

    """
    try:
        # Getting the mongodb client, that talks to Program_History
        collector = get_collector(collection="Program_History")

        # In the pipeline we need to set the mainprogflg to True, because there is two program history with same
        # Timestamp, one for mainprogflg true another for false

        pipeline = [
            {
                '$match': {
                    'enddate': {
                        '$gt': search_time
                    },
                    'mainprogflg': True
                }
            }, {
                '$sort': {
                    'enddate': 1
                }
            }
        ]

        data = list(collector.aggregate(pipeline))

        if data:
            return data

        return None

    except ServerSelectionTimeoutError as error:
        LOGGER.exception(f"Unable to select mongodb server with following error: {error.args[0]}")
        raise MongoDbConnectionFailure("Error from 'get_program_history'")
    except ConnectionFailure as error:
        LOGGER.exception(f"Unable to make connection to database server with following error: {error.args[0]}")
        raise MongoDbConnectionFailure("Error from 'get_program_history'")
    except NetworkTimeout as error:
        LOGGER.exception(f"Network timed out with following error: {error.args[0]}")
        raise MongoDbConnectionFailure("Error from 'get_program_history'")
    except OperationFailure as error:
        LOGGER.exception(f"The database operation failed with following error: {error.args[0]}")
        raise MongoDbConnectionFailure("Error from 'get_program_history'")


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
    except TimescaleDbConnectionFailure as error:
        LOGGER.exception(f"Error While getting reference signal from timescaledb: {error.args[0]}")
        raise GetReferenceSignalFailure("Error from 'get_reference_signal'")
    except Exception as error:
        LOGGER.exception(f"Error While getting reference signal from timescaledb: {error.args[0]}")
        raise GetReferenceSignalFailure("Error from 'get_reference_signal'")


def get_dynamic_config(parameter_id=17):
    """

    Function used to get the configuration details of dynamic parameter groups

    :param parameter_id: The id of the parameter group (in timescaledb) for which the details are to be
    returned
    :type parameter_id: int

    :return: The list containing the dynamic parameter configuration details for the given parameter id
    :rtype: list | None

    """

    try:
        # Query to return the reference signal value for the given parameter
        query = f"""
                SELECT group_name, mongodb_query, latest_update_time
                FROM tiei_sample_4.parameters_group
                WHERE id = {parameter_id};
                """

        dynamic_config = execute_read_query_timescaledb(query)[0]

        if dynamic_config:
            return dynamic_config

        return None
    except TimescaleDbConnectionFailure as error:
        LOGGER.exception(f"Error While getting dynamic parameter config from timescaledb: {error.args[0]}")
        raise GetDynamicConfigFailure("Error from 'get_dynamic_config'")
    except Exception as error:
        LOGGER.exception(f" Unknown Error While getting dynamic parameter from timescaledb: {error.args[0]}")
        raise GetDynamicConfigFailure("Error from 'get_dynamic_config'")


def get_static_config():
    """

    Function used to get the configuration details of static parameter groups

    :return: The list containing the list of static parameter configuration details
    :rtype: list | None

    """

    try:
        # Query to return the reference signal value for the given parameter
        non_static_parameters = 17

        query = f"""
                SELECT "group_name", "mongodb_query", "latest_update_time", 
                "warning_limit", "critical_limit", "parameter_type"
                FROM tiei_sample_4.parameters_group
                WHERE id != {non_static_parameters};
                """

        static_config = execute_read_query_timescaledb(query)

        if static_config:
            return static_config

        return None
    except TimescaleDbConnectionFailure as error:
        LOGGER.exception(f"Error While getting dynamic parameter config from timescaledb: {error.args[0]}")
        raise GetDynamicConfigFailure("Error from 'get_dynamic_config'")
    except Exception as error:
        LOGGER.exception(f" Unknown Error While getting dynamic parameter from timescaledb: {error.args[0]}")
        raise GetDynamicConfigFailure("Error from 'get_dynamic_config'")


def get_parameter_group_config():
    """

    Function used to get the configuration details of all parameter groups

    :return: The list containing the list of static parameter configuration details
    :rtype: list | None

    """

    try:
        # Query to return the reference signal value for the given parameter

        query = f"""
                SELECT "id", "mongodb_query", "warning_limit", "critical_limit", "parameter_type"
                FROM tiei_sample_4.parameters_group;
                """

        config = execute_read_query_timescaledb(query)

        if config:
            return config

        return None
    except TimescaleDbConnectionFailure as error:
        LOGGER.exception(f"Error While getting dynamic parameter config from timescaledb: {error.args[0]}")
        raise GetDynamicConfigFailure("Error from 'get_parameter_group_config'")
    except Exception as error:
        LOGGER.exception(f" Unknown Error While getting dynamic parameter from timescaledb: {error.args[0]}")
        raise GetDynamicConfigFailure("Error from 'get_parameter_group_config'")


def update_latest_time(group_name="dynamic_parameters", update_time=datetime.utcfromtimestamp(1648205580)):
    """

    Function used to update the latest update_time for a given parameter group

    :param group_name: The parameter group name that needs to be updated
    :type group_name: str

    :param update_time: The latest update time for the parameter group
    :type update_time: datetime

    :return: Nothing
    :rtype: None

    """

    try:
        # Query to return the reference signal value for the given parameter
        query = f"""
                UPDATE tiei_sample_4.parameters_group
                SET latest_update_time= '{update_time}'
                WHERE group_name = '{group_name}';
                """

        execute_update_query_timescaledb(query)

        LOGGER.debug("Updated latest update time")

        # 1648205580
    except TimescaleDbConnectionFailure as error:
        LOGGER.exception(f"Error While updating latest update time into timescaledb: {error.args[0]}")
        raise SetDynamicConfigFailure("Error from 'update_latest_time'")
    except Exception as error:
        LOGGER.exception(f" Unknown Error updating latest update time into timescaledb: {error.args[0]}")
        raise SetDynamicConfigFailure("Error from 'update_latest_time'")


def insert_parameters_from_mongo_to_timescale():
    """

    Function to insert all the parameters from mongodb to timescaledb

    :return: Nothing
    :rtype: None

    """

    try:

        all_machine_parameters = get_machine_parameters_all_mongo()

        table_name = "machine_parameters"
        table_column_names = ("name", "parameter_group_id", "warning_limit", "critical_limit", "parameter_type",
                              "machine_id", "unit_id")
        db_schema = "tiei_sample_4"

        insert_new_data_bulk_timescaledb(records=all_machine_parameters, table_name=table_name,
                                         table_column_names=table_column_names, db_schema=db_schema)

    except ServerSelectionTimeoutError as error:
        LOGGER.exception(f"Unable to select mongodb server with following error: {error.args[0]}")
    except ConnectionFailure as error:
        LOGGER.exception(f"Unable to make connection to database server with following error: {error.args[0]}")
    except NetworkTimeout as error:
        LOGGER.exception(f"Network timed out with following error: {error.args[0]}")
    except OperationFailure as error:
        LOGGER.exception(f"The database operation failed with following error: {error.args[0]}")
    except TimescaleDbConnectionFailure as error:
        LOGGER.exception(f"Error While getting reference signal from timescaledb: {error.args[0]}")
    except Exception as error:
        LOGGER.exception(f"Error While getting reference signal from timescaledb: {error.args[0]}")


def insert_parameters_group_to_timescale():
    """

    Function to insert all the parameters group information from the config file to timescaledb

    :return: Nothing
    :rtype: None

    """

    try:
        file_name = PARAMETER_CONFIG + "parameters_config.json"

        parameters_group_info = pd.read_json(file_name)

        pprint.pprint(parameters_group_info.head())

        parameters_group_info = parameters_group_info[["group_name", "mongodb_query", "latest_update_time",
                                                       "warning_limit", "critical_limit", "parameter_type"]]

        pprint.pprint(parameters_group_info.head())
        table_name = "parameters_group"
        table_column_names = ("group_name", "mongodb_query", "latest_update_time", "warning_limit",
                              "critical_limit", "parameter_type")
        db_schema = "tiei_sample_4"

        insert_new_data_bulk_timescaledb(records=parameters_group_info.values.tolist(), table_name=table_name,
                                         table_column_names=table_column_names, db_schema=db_schema)

    except ServerSelectionTimeoutError as error:
        LOGGER.exception(f"Unable to select mongodb server with following error: {error.args[0]}")
    except ConnectionFailure as error:
        LOGGER.exception(f"Unable to make connection to database server with following error: {error.args[0]}")
    except NetworkTimeout as error:
        LOGGER.exception(f"Network timed out with following error: {error.args[0]}")
    except OperationFailure as error:
        LOGGER.exception(f"The database operation failed with following error: {error.args[0]}")
    except TimescaleDbConnectionFailure as error:
        LOGGER.exception(f"Error While getting reference signal from timescaledb: {error.args[0]}")
    except Exception as error:
        LOGGER.exception(f"Error While getting reference signal from timescaledb: {error.args[0]}")


def main():
    """

    Main function to call appropriate functions to carry out required task.

    :return: Nothing
    :rtype: None

    """
    # records = get_machine_parameters_count()
    # insert_new_data_bulk_timescaledb(records)
    # get_machine_parameters_all("T_H_OP180A")
    # get_machines_id_timescaledb()

    # get_parameters_id_timescaledb()

    # x = get_machine_parameters_all("TEST")
    # print(x)

    # d = get_program_history()
    # pprint.pprint(d)

    # get_reference_signal(405)

    #insert_parameters_group_to_timescale()

    # update_latest_time()
    #get_machine_parameters_all_mongo()
    insert_parameters_from_mongo_to_timescale()

    #get_machine_parameters_count()

    #insert_machines_from_mongo_to_timescale()

    #get_machine_parameters_all_mongo()


if __name__ == '__main__':
    main()
