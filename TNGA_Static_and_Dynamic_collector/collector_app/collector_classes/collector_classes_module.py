#!/usr/bin/python
# -*- coding: utf-8 -*-
"""

COLLECTOR CLASSES
======================

Module that has all the required classes for the collector app to work

This script requires the following modules be installed in the python environment

    Standard Library
    =================

    * logging - to perform logging operations
    * datetime - to perform date and time related operations
    * abc - to create abstract classes
    * time - to perform time related operations

    Related 3rd Party Library
    =============================

    * pandas - to perform data manipulation and analysis

This script contains the following function
    * main - main function to carry out appropriate task to run the collector system

This script contains the following classes
    * ParametersGroupAbstract - The abstract class for all parameters group
    * ParametersGroupBase - The base class for all parameters group
    * CollectorClass - The class to represent the collector system

"""

# Standard library imports
import datetime
from datetime import timezone
import sys

import logging
from abc import ABC, abstractmethod
import time
from typing import Union

# Related third party imports
import pandas as pd
from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure, NetworkTimeout, OperationFailure
import numpy as np

# Local application/library specific imports
from collector_app.database.db_utils import get_collector, \
    get_parameters_id_timescaledb, get_spindle_servo_params_mongo, get_program_history, get_reference_signal, \
    read_data_timescaledb, get_dynamic_config, update_latest_time, get_static_config, \
    get_parameters_limits_timescaledb, get_reference_signal_variants

from collector_app.database.crud_operations import (insert_new_data_bulk_timescaledb, update_data_bulk_timescaledb,
                                                    update_corrective_activities_bulk)

from collector_app.database.common_query_templates import get_check_new_data_template, get_new_data_template, \
    get_dynamic_data_template

from collector_app.report_manager import EMAIL_SERVER, RECEIVER_EMAIL, EMAIL_REPORT_ROOT_DIRECTORY, \
    EMAIL_REPORT_ROOT_DIRECTORY_TEMP
from collector_app.utils.config_helper import load_config_data

from collector_app.collector_classes import DEFAULT_PARAMETER_CONFIG_PATH

from collector_app.anomaly_detection.detection_algorithm import kruskal_test

from collector_app.exception_helper.custom_exception_classes import NoDataFromMongoDB, MongoDbConnectionFailure, \
    ParameterIdQueryFailure, MtLinkiGetNewDataParametersGroupClassFailure, \
    AddConditionColumnParametersGroupClassFailure, InsertTimescaleParametersGroupClassFailure, \
    TimescaleDbConnectionFailure, CheckAnomalyParametersGroupClassFailure, SendAnomalyParametersGroupClassFailure, \
    LoadConfigFailure, LoadParamCollectorClassFailure, WorkflowCollectorClassFailure, \
    MergeAlertsCollectorClassFailure, SendAlertsCollectorClassFailure, SetDynamicConfigFailure

from collector_app.database.db_utils import get_axis_group_details, get_axis_group_details_pony
from collector_app.report_manager.email_sender import create_excel_report

from collector_app.database.operation.orm import read_operation, update_operation

__author__ = "smt18m005@iiitdm.ac.in"

LOGGER = logging.getLogger(__name__)


class ParametersGroupAbstract(ABC):
    """
    ABSTRACT CLASS FOR ALL PARAMETERS GROUP
    ===========================================

    This represents the abstract class that should be inherited by any class representing a parameter group
    """

    def __init__(self, group_name, mongodb_query, latest_update_time, warning_limit=None, critical_limit=None,
                 parameter_type="decreasing"):
        """

        INITIALIZATION
        ================

        :param group_name: The name of the parameters group
        :type group_name: str

        :param mongodb_query: The regex query pattern to used for querying the mongodb
        :type mongodb_query: str

        :param latest_update_time: The time at which the MtLinki was queried last time - Should be in epoch format (
        seconds)
        :type latest_update_time: datetime.datetime

        :param warning_limit: The limit after which the parameter is considered to be in warning state
        :type warning_limit: int | float

        :param critical_limit: The limit after which the parameter is considered to be in critical state
        :type critical_limit: int | float

        :param parameter_type: The variable which denotes of the parameters value is of type bool or increasing (
        meaning the critical value is greater than the warning value) or decreasing (meaning the critical values is
        smaller than the warning value)
        :type parameter_type: str

        """
        self.group_name = group_name
        self.mongodb_query = mongodb_query
        self.warning_limit = warning_limit
        self.critical_limit = critical_limit

        # Remember that everything should be in utc (as it is in Mtlinki) and in seconds
        # self.latest_update_time = datetime.datetime.utcfromtimestamp(latest_update_time)
        self.latest_update_time = latest_update_time

        # This represents the temporary latest update time, this will be used to change the
        # Actual latest update time after insertion of data into timescaledb
        # self._temp_latest_update_time = datetime.datetime.utcfromtimestamp(latest_update_time)
        self._temp_latest_update_time = latest_update_time

        self.parameter_type = parameter_type

        # This attribute will be updated with latest data from Mtlinki (If available)
        self.recent_data = None

        self.recent_abnormal_data = None

        self.recent_new_activity_data = None

        self.recent_existing_activity_data = None

        self.recent_critical_data = None

        self.ignored_parameter_list = read_operation.get_ignored_parameter_ids()

        # This dictionary stores the next time when an alert for a signal (parameter)
        # Should be sent, for instance {500: "2022-06-25T17:10:30"}
        # This denotes that the parameter with id 500 (as stored in timescaledb)
        # Should not send an alert until a new alert (not in OK condition) for this signal (500) is generated with
        # an updatetime greater than  2022-06-25T17:10:30. This time (2022-06-25T17:10:30) is generated when
        # The signal created an alert for the first time ( by adding 8 hour with the updatetime)
        # for example 2022-06-25T06:10:30 + 8 hours  = 2022-06-25T17:10:30, where 2022-06-25T06:10:30 is the
        # updatetime when the signal was in critical/warning condition for the first time
        self.next_alert_time_for_all_signals = {}

        # This is used to store the new alerts during the current read cycle (if available)
        self.new_alerts = None

        self.warning_map, self.critical_map, self.display_name_map, self.group_name_map =\
            read_operation.query_all_machine_parameters()

        LOGGER.info("Initialized")

    @abstractmethod
    def check_for_new_data(self):
        """
        This method is used to check if new data is available.
        This method is deprecated now

        :return: Nothing
        :rtype: None
        """
        pass

    @abstractmethod
    def get_new_data(self):
        """
        This method is used to query the MtLinki for new data

        :return: Nothing
        :rtype: None
        """
        pass

    @abstractmethod
    def add_condition_columns(self):
        """
        This method is used to add new column to the dataframe, which denotes the condition of the parameter

        :return: Nothing
        :rtype: None
        """
        pass

    @abstractmethod
    def insert_to_timescaledb(self):
        """
        This function is used to insert the new data from MtLinki into TimescaleDB

        :return: Nothing
        :rtype: None
        """
        pass

    @abstractmethod
    def check_activity(self):
        """
        This function is used to check the recent abnormal data with the activity table

        :return: Nothing
        :rtype: None
        """
        pass

    @abstractmethod
    def insert_new_activity(self):
        """
        This function is used to insert the new abnormal data into activity table

        :return: Nothing
        :rtype: None
        """
        pass

    @abstractmethod
    def update_existing_activity(self):
        """
        This function is used to update the existing abnormal data into activity table

        :return: Nothing
        :rtype: None
        """
        pass

    @abstractmethod
    def check_for_new_anomaly(self):
        """
        This methods is used to check if any new anomalies have be generated

        :return: Nothing
        :rtype: None
        """
        pass

    @abstractmethod
    def send_alerts(self):
        """
        This method is used to send alerts through email

        :return: Nothing
        :rtype: None
        """
        pass


class ParametersGroupBase(ParametersGroupAbstract):
    """

    This represents the base class for all parameters group

    """

    def check_for_new_data(self):
        """

        Deprecated
        :return:
        :rtype:

        """

        try:

            collector = get_collector("L1Signal_Pool")
            pipeline = get_check_new_data_template(self.mongodb_query)

            data = collector.aggregate(pipeline)

            # If there is an error connecting to mongodb, or return an empty list, raise the following error
            if not list(data):
                raise NoDataFromMongoDB

            current_time = float(data.next()["updatedate"].to_decimal())
            new_files = current_time > self.latest_update_time

            return new_files

        except NoDataFromMongoDB as error:

            LOGGER.exception(f"Exception while checking for new data, seems to return empty list: {error}")
            raise NoDataFromMongoDB

    def get_new_data(self):
        """

        This function works by querying the MtLinki database (collection: L1Signal_Pool_Active) for static parameters
        data  with updatedate time greater than the last time a new data was queried.

        Only the static parameters are queried, since they have a read rate of 60 seconds,
        the dynamic parameters have a read rate of 0.5 seconds (hence they have to queried from "L1Signal_Pool")
        which will be carried out in a different function.

        """

        try:

            # Getting the mongodb client, that talks to L1Signal_Pool_Active
            collector = get_collector(collection="L1Signal_Pool_Active")

            # Getting the mongodb query parameter
            find_query = get_new_data_template(regex_pattern=self.mongodb_query,
                                               search_time=self.latest_update_time)

            LOGGER.info(f"Latest Update Time for the group: {self.group_name} is {self.latest_update_time}")

            # Projecting only required fields
            projection_fields = {"signalname": 1, "updatedate": 1, "L1Name": 1, "value": 1, "_id": 0}

            # Getting the data
            data = collector.find(find_query, projection_fields).sort("updatedate", 1)
            data = list(data)
            LOGGER.debug(len(data))
            LOGGER.debug(data)

            # If data is available
            if data:

                # We set the recent_data attribute to a pandas dataframe with values equal to the query result
                self.recent_data = pd.DataFrame(data)

                LOGGER.info(f"The start time of the result: is {self.recent_data.iloc[0, :]}")
                LOGGER.info(f"The end time of the result: is {self.recent_data.iloc[-1, :]}")

                LOGGER.debug(self.recent_data.iloc[-1, :])

                # We need to set the latest update time only after the insertion of data into timescaledb,
                # Because if database insertion operation fails, then we need to again query those data from
                # Mongodb and then insert ,hence only after successfully insertion we should update this
                # Check in the insert_to_timescaledb method

                # We set the latest_update_time equal to the latest (max of updatedate) timestamp of any recorded
                # Signal, we take the last from the dataframe, since the data is already sorted in ascending order
                self._temp_latest_update_time = self.recent_data.iat[-1, 1].to_pydatetime()
                LOGGER.debug(self._temp_latest_update_time)
                LOGGER.debug("LAST TIME")

                # The result from MtLinki will have only the signalname, this has to be converted to the actual
                # id of the parameter (to be) stored in the timescaledb, in table "machine_parameters"
                # Hence, getting the ids for all signalname.
                parameter_id_mapping = get_parameters_id_timescaledb()

                data_warning_mapping, data_critical_mapping, display_name = get_parameters_limits_timescaledb()

                # Creating a new column in the df called "parameters and setting it equal to the signalname column
                self.recent_data["parameters"] = self.recent_data["signalname"]
                self.recent_data["warning_limit"] = self.recent_data["signalname"]
                self.recent_data["critical_limit"] = self.recent_data["signalname"]
                self.recent_data["Parameter"] = self.recent_data["signalname"]
                self.recent_data["Axis"] = self.recent_data["signalname"]

                # Mapping all the signalname to id column of the table "machine_parameters"
                # (such as 44 for ApcBatLow_0_path1_T_B_OP160) and it's corresponding limits
                self.recent_data["signalname"] = self.recent_data["signalname"].map(parameter_id_mapping)
                self.recent_data["warning_limit"] = self.recent_data["warning_limit"].map(data_warning_mapping)
                self.recent_data["critical_limit"] = self.recent_data["critical_limit"].map(data_critical_mapping)
                self.recent_data["Parameter"] = self.recent_data["Parameter"].map(self.group_name_map)
                self.recent_data["Axis"] = self.recent_data["Axis"].map(self.display_name_map)
                LOGGER.debug(self.recent_data.head())
            else:
                # If new data is not available, we set it to None (This is important, else it will work with
                # Previous read cycle's data
                self.recent_data = None

        except ServerSelectionTimeoutError as error:
            LOGGER.exception(f"Unable to select mongodb server with following error: {error}")
            self.recent_data = None
            raise MtLinkiGetNewDataParametersGroupClassFailure(error)
        except ConnectionFailure as error:
            LOGGER.exception(f"Unable to make connection to database server with following error: {error}")
            self.recent_data = None
            raise MtLinkiGetNewDataParametersGroupClassFailure(error)
        except NetworkTimeout as error:
            LOGGER.exception(f"Network timed out while connecting to database server with following error: {error}")
            self.recent_data = None
            raise MtLinkiGetNewDataParametersGroupClassFailure(error)
        except OperationFailure as error:
            LOGGER.exception(f"The database operation failed with following error: {error}")
            self.recent_data = None
            raise MtLinkiGetNewDataParametersGroupClassFailure(error)
        except ParameterIdQueryFailure as error:
            LOGGER.exception(f"Couldn't get the parameters id from the timescaledb due to following error: {error}")
            self.recent_data = None
            raise MtLinkiGetNewDataParametersGroupClassFailure(error)
        except Exception as error:
            LOGGER.exception(f"error {error}")
            self.recent_data = None
            raise MtLinkiGetNewDataParametersGroupClassFailure(error)

    def add_condition_columns(self):
        """

        This method works by converting all the values less (greater in case of decreasing type parameter) than the
        warning limit to condition (id) of 1 (OK condition), less than critical limit (but greater than warning)
        as condition (id) of 2 (Warning condition), greater than critical limit as condition (id) of 3 (Critical
        Condition)

        """

        try:

            # If recent data is empty (None) we do not add any columns
            if self.recent_data is None:
                LOGGER.debug("No New Data")
                return

            # We create new column called condition equal 1
            self.recent_data["condition"] = 1
            LOGGER.debug(self.recent_data.head())

            if self.parameter_type == "decreasing":

                # If the parameter type is decreasing, we do the following

                # Map all the values in column "condition" to 1, if the corresponding value in column "value"
                # Is greater than the warning limit, if it is less than warning but greater than critical
                # We set it to 2, if less than critical limit, we set it to 3
                # self.recent_data["condition"].
                # mask(self.recent_data["value"] > self.warning_limit, 1, inplace=True)
                # self.recent_data["condition"].
                # mask(self.recent_data["value"] < self.warning_limit - 1, 2, inplace=True)
                # self.recent_data["condition"].
                # mask(self.recent_data["value"] < self.critical_limit - 1, 3, inplace=True)
                self.recent_data["condition"] = np.where(
                    (self.recent_data["value"].notnull()) &
                    (self.recent_data["value"] <= self.recent_data["critical_limit"]),
                    3, self.recent_data["condition"])

                self.recent_data["condition"] = np.where(
                    (self.recent_data["value"].notnull()) &
                    (self.recent_data["value"] <= self.recent_data["warning_limit"]) &
                    (self.recent_data["value"] > self.recent_data["critical_limit"]),
                    2, self.recent_data["condition"])

                # Override condition to 1 (OK) for ignored parameters
                self.recent_data['condition'] = np.where(
                    self.recent_data['signalname'].isin(self.ignored_parameter_list),
                    1,
                    self.recent_data['condition']
                )
                LOGGER.info("ok")

            elif self.parameter_type == "increasing":

                # If parameter is of type increasing do the following

                # Map all the values in column "condition" to 1, if the corresponding value in column "value"
                # Is less than the warning limit, if it is greater than warning but less than critical
                # # We set it to 2, if greater than critical limit, we set it to 3
                # self.recent_data["condition"].
                # mask(self.recent_data["value"] < self.warning_limit, 1, inplace=True)
                # self.recent_data["condition"].
                # mask(self.recent_data["value"] > self.warning_limit - 1, 2, inplace=True)
                # self.recent_data["condition"].
                # mask(self.recent_data["value"] > self.critical_limit - 1, 3, inplace=True)

                self.recent_data["condition"] = np.where(
                    (self.recent_data["value"].notnull()) &
                    (self.recent_data["value"] >= self.recent_data["critical_limit"]),
                    3, self.recent_data["condition"])

                self.recent_data["condition"] = np.where(
                    (self.recent_data["value"].notnull()) &
                    (self.recent_data["value"] >= self.recent_data["warning_limit"]) &
                    (self.recent_data["value"] < self.recent_data["critical_limit"]),
                    2, self.recent_data["condition"])

                # Override condition to 1 (OK) for ignored parameters
                self.recent_data['condition'] = np.where(
                    self.recent_data['signalname'].isin(self.ignored_parameter_list),
                    1,
                    self.recent_data['condition']
                )
                LOGGER.info("ok")

            elif self.parameter_type == "bool":

                # If parameter is of type boolean, do the following

                # We map all the true values to 1, and false to 0 in the "value" column
                # Since in Timescaledb we cannot have mixed value type in a column, hence we're converting it from
                # Boolean to float
                self.recent_data["value"] = self.recent_data["value"].map({True: 1, False: 0})

                # Mapping all 1 to 3 (True to 3, critical condition, such in "ApcBatLow_0_path1_T_B_OP160"
                # Where true denotes battery is low), and 0 to 1 (False to 1 - OK condition)
                self.recent_data["condition"].mask(self.recent_data["value"] == 1, 3, inplace=True)
                self.recent_data["condition"].mask(self.recent_data["value"] == 0, 1, inplace=True)

            LOGGER.debug(self.recent_data.tail())

            if self.group_name == "SERVO_SPINDLE_INSULATION_RESISTANCE":
                self.recent_data["condition"]. \
                    mask(self.recent_data["value"] == 0, 1, inplace=True)

        except Exception as error:
            self.recent_data = None
            LOGGER.exception(f"Unknown Error While adding Condition Column to the recent data: {error}")
            raise AddConditionColumnParametersGroupClassFailure(error)

    def insert_to_timescaledb(self):

        try:

            # If no new data is available, we skip the remaining of the code
            if self.recent_data is None:
                LOGGER.debug("No New Data")
                return

            records = self.recent_data.loc[:, ["updatedate", "signalname", "value", "condition"]].to_numpy().tolist()

            if self.group_name == "DYNAMIC_PARAMETERS":

                # if this parameter is of type DYNAMIC_PARAMETERS, then we need to drop all rows
                # That doesn't have condition id
                records_active = self.recent_data[self.recent_data['condition'].notna()]

                records_active = records_active.loc[:, ["updatedate", "signalname",
                                                        "value", "condition"]].to_numpy().tolist()
            else:
                records_active = self.recent_data.loc[:, ["updatedate", "signalname",
                                                          "value", "condition"]].to_numpy().tolist()

            table_name = "real_time_machine_parameters"
            table_column_names = ("time", "machine_parameters_id", "value", "condition_id")
            db_schema = "tiei_sample_4"

            # errors here will raise TimescaleDbConnectionFailure error
            insert_new_data_bulk_timescaledb(records=records, table_name=table_name,
                                             table_column_names=table_column_names, db_schema=db_schema)

            LOGGER.debug("INSERTED DATA INTO TIMESCALEDB")

            active_records_tuple = tuple({"time": record_data[0], "machine_parameters_id": record_data[1],
                                          "value": record_data[2], "condition_id": record_data[3]}
                                         for record_data in records_active)

            update_data_bulk_timescaledb(records=active_records_tuple)

            LOGGER.debug("UPDATED DATA INTO TIMESCALEDB")

            update_latest_time(group_name=self.group_name, update_time=self._temp_latest_update_time)

            # We set the latest_update_time equal to the latest (max of updatedate) timestamp of any recorded
            # Signal, we take the last from the dataframe, since the data is already sorted in ascending order
            self.latest_update_time = self._temp_latest_update_time
            LOGGER.info(f"The Latest Update time is successfully updated: {self.latest_update_time}")

            # We are filter out the recent data to include only the warning and critical data
            # Which could be further be used for anomaly monitoring and sending alerts
            # Hence this has to be called before checking for anomaly or sending alerts
            # Else all data (including OK) will be considered as anomaly and will be sent as alerts
            self.recent_abnormal_data = self.recent_data[(self.recent_data["condition"] > 1)]
            # self.recent_abnormal_data = self.recent_data[(self.recent_data["condition"] > 0)]
            self.recent_critical_data = self.recent_data[(self.recent_data["condition"] == 3)]

            # We do this extra step for the dynamic parameters group, since for those, only the last
            # data will have condition value, everything else will be Null/None
            self.recent_abnormal_data = self.recent_abnormal_data[self.recent_abnormal_data["condition"].notnull()]
            self.recent_critical_data = self.recent_critical_data[self.recent_critical_data["condition"].notnull()]

            # If the there is no new critical anomaly, we can set the recent_critical_data to None, which will make the
            # Next steps (checking for anomaly, sending alerts) to be skipped.
            if self.recent_critical_data.empty:
                self.recent_critical_data = None

            # If the there is no new anomaly, we can set the recent_data to None, which will make the
            # Next steps (checking for anomaly, sending alerts) to be skipped.
            if self.recent_abnormal_data.empty:
                self.recent_abnormal_data = None

        except TimescaleDbConnectionFailure as error:
            LOGGER.exception(f"Unknown Error While inserting recent data to timescaledb: {error.args[0]}")
            self.recent_data = None
            sys.exit(-1)
            # raise InsertTimescaleParametersGroupClassFailure("Data Insertion Error")
        except SetDynamicConfigFailure as error:
            LOGGER.exception(f"Error while updating the latest update time for the parameter"
                             f"group into to timescaledb: {error.args[0]}")
            self.recent_data = None
            sys.exit(-1)
            # raise InsertTimescaleParametersGroupClassFailure("Data Insertion Error")
        except Exception as error:
            LOGGER.exception(f"Unknown Error While inserting recent data to timescaledb: {error.args[0]}")
            self.recent_data = None
            sys.exit(-1)
            # raise InsertTimescaleParametersGroupClassFailure("Data Insertion Error")

    def check_activity(self):

        # If no new data is available, we skip the remaining of the code
        if self.recent_abnormal_data is None:
            LOGGER.info("No New Abnormal Data")
            self.recent_new_activity_data = None
            self.recent_existing_activity_data = None
            return

        parameter_ids = self.recent_abnormal_data['signalname'].unique().tolist()
        unique_combinations = (self.recent_abnormal_data[['signalname', 'condition']].
                               drop_duplicates().apply(tuple, axis=1).tolist())

        #existing_ids = read_operation.select_activities_by_machine_params(parameter_ids)
        existing_ids = read_operation.select_activities_by_machine_params_condition(unique_combinations)

        new_ids = list(set(parameter_ids) - set(existing_ids))

        LOGGER.info(f"New Data Length: {len(new_ids)}")
        LOGGER.info(f"Existing Data Length: {len(existing_ids)}")

        if new_ids:
            # Filter abnormal data for new activities
            self.recent_new_activity_data =\
                self.recent_abnormal_data[self.recent_abnormal_data['signalname'].isin(new_ids)]
        else:
            self.recent_new_activity_data = None

        if existing_ids:
            # Filter abnormal data for existing activities
            self.recent_existing_activity_data = self.recent_abnormal_data[
                self.recent_abnormal_data['signalname'].isin(existing_ids)]
        else:
            self.recent_existing_activity_data = None

    def insert_new_activity(self):

        # If no new data is available, we skip the remaining of the code
        if self.recent_new_activity_data is None:
            LOGGER.debug("No New Activity Data")
            return

        record = self.recent_new_activity_data.loc[:, ["signalname", "updatedate", "condition", "value"]]
        record["latest_occurrence"] = record["updatedate"]
        record['number_of_occurrences'] = 1  # Add constant value to new column

        table_name = "corrective_activity"
        table_column_names = ("machine_parameters_id", "date_of_identification", "parameter_condition_id",
                              "recent_value", "latest_occurrence",
                              "number_of_occurrences")

        db_schema = "tiei_sample_4"

        record_list = record.to_numpy().tolist()

        # errors here will raise TimescaleDbConnectionFailure error
        insert_new_data_bulk_timescaledb(records=record_list, table_name=table_name,
                                         table_column_names=table_column_names, db_schema=db_schema)

        LOGGER.debug("INSERTED DATA INTO TIMESCALEDB From Abnormal")

    def update_existing_activity(self):

        # If no new data is available, we skip the remaining of the code
        if self.recent_existing_activity_data is None:
            LOGGER.debug("No Existing Activity Data")
            return
        LOGGER.info("In Update")

        update_operation.update_corrective_activities_from_dataframe(self.recent_existing_activity_data)

        LOGGER.info("UPDATED DATA INTO TIMESCALEDB From abnormal data")

    def check_for_new_anomaly(self):

        try:

            # If no new data is available, we skip the remaining of the code
            if self.recent_critical_data is None:
                LOGGER.debug("No New Data")
                self.new_alerts = None
                return

            self.recent_critical_data["next_alert_time"] = self.recent_critical_data["signalname"]
            self.recent_critical_data['next_alert_time'] = self.recent_critical_data['signalname']. \
                map(self.next_alert_time_for_all_signals)
            LOGGER.debug(self.recent_critical_data.head())

            # Getting only the data which was already existing in the "next_alert_time_for_all_signals" attribute
            # By filtering only non-null values, since the above mapping will result in null values if the value is not
            # found in the keys of the given dictionary
            existing_new_alerts = self.recent_critical_data[self.recent_critical_data['next_alert_time'].notnull()]

            # Only if there is any new alerts for existing signals, we do the following
            if not existing_new_alerts.empty:

                # We first filter out only those rows that have latest update time greater than the next_alert_time
                existing_new_alerts = existing_new_alerts[
                    (existing_new_alerts["updatedate"] > existing_new_alerts["next_alert_time"])]

                # We do the following only if after filter, there is some new data
                if not existing_new_alerts.empty:
                    # Saving the new time for next alerts for existing signals
                    next_alert_time_df = existing_new_alerts.copy(deep=True)

                    # We set the next alert time to the current "updatedate" time + 8 hours (the grace period we give
                    # Until the same parameter needs to be reported when it is not in OK condition)
                    next_alert_time_df["next_alert_time"] = next_alert_time_df["updatedate"] + \
                                                            pd.to_timedelta(4, unit='h')

                    if "warning_limit" in next_alert_time_df.columns:
                        # Dropping unwanted columns
                        next_alert_time_df = next_alert_time_df.drop(columns=["updatedate", "value", "condition",
                                                                              "L1Name", "parameters", "warning_limit",
                                                                              "critical_limit"])
                    else:
                        # Dropping unwanted columns
                        next_alert_time_df = next_alert_time_df.drop(columns=["updatedate", "value", "condition",
                                                                              "L1Name", "parameters"])

                    # Converting the dataframe to dictionary, whose key are the signal name (id) and values
                    # Are the latest updatedate plus 8 hours
                    next_alert_time_dict = next_alert_time_df.set_index("signalname").T.to_dict("list")

                    # The above dictionary will have the next alert time in a list, so in the below code
                    # We remove the time by accessing the list
                    next_alert_time_dict = {parameters_id: next_alert_time[0] for parameters_id, next_alert_time
                                            in next_alert_time_dict.items()}

                    # Updating the old dictionary that stores the "next_alert_time_for_all_signals" with the new time
                    # Generated from the new signals that were not in OK condition
                    self.next_alert_time_for_all_signals.update(next_alert_time_dict)
                    LOGGER.debug("NEW ALERTS EXISTING DICTIONARY")
                    LOGGER.debug(self.next_alert_time_for_all_signals)

            # All the data that were not filtered out previously fall under the category of new alerts
            # Meaning this signal was never in warning/critical condition and was not previously stored
            # In self.next_alert_time_for_all_signals dictionary
            new_alerts = self.recent_critical_data[self.recent_critical_data['next_alert_time'].isnull()]
            LOGGER.debug("NEW ALERTS")
            LOGGER.debug(new_alerts.head())

            # Only if there is any new alerts for new signals(that were not previously stored), we do the following
            if not new_alerts.empty:
                # Saving the new time for next alerts for new signals
                next_alert_time_df = new_alerts.copy(deep=True)

                # We set the next alert time to the current "updatedate" time + 8 hours (the grace period we give
                # Until the same parameter needs to be reported when it is not in OK condition)
                next_alert_time_df["next_alert_time"] = (next_alert_time_df["updatedate"] +
                                                         pd.to_timedelta(4, unit='h'))

                if "warning_limit" in next_alert_time_df.columns:
                    # Dropping unwanted columns
                    next_alert_time_df = next_alert_time_df.drop(
                        columns=["updatedate", "value", "condition", "L1Name", "parameters", "warning_limit",
                                 "critical_limit"])
                else:
                    # Dropping unwanted columns
                    next_alert_time_df = next_alert_time_df.drop(
                        columns=["updatedate", "value", "condition", "L1Name", "parameters"])

                # Converting the dataframe to dictionary, whose key are the signal name (id) and values
                # Are the latest updatedate plus 8 hours
                # This will raise an issue, because the program history might have more than two cycle's data
                # That needs to be checked and added, but in that case, the same signal id will be having condition
                # Value equal to 2 or 3 (corresponding to the two or more cycles), in that case some index will be
                # omitted directly by pandas, currently this is fine, if any issue occurs change the logic
                next_alert_time_dict = next_alert_time_df.set_index("signalname").T.to_dict("list")

                # The above dictionary will have the next alert time in a list, so in the below code
                # We remove the time by accessing the list
                next_alert_time_dict = {parameters_id: next_alert_time[0] for parameters_id, next_alert_time in
                                        next_alert_time_dict.items()}

                # Updating the old dictionary that stores the "next_alert_time_for_all_signals" with the new time
                # Generated from the new signals that were not in OK condition
                self.next_alert_time_for_all_signals.update(next_alert_time_dict)
                LOGGER.debug("NEW ALERTS DICTIONARY")
                LOGGER.debug(self.next_alert_time_for_all_signals)

            # The following code will be executed only if any one (or both) of alerts (existing signals or new signals)
            # is not empty
            if (not existing_new_alerts.empty) or (not new_alerts.empty):

                # We set the new alerts to be union of two alert data
                self.new_alerts = pd.concat([existing_new_alerts.drop(columns=["signalname", "next_alert_time"]),
                                             new_alerts.drop(columns=["signalname", "next_alert_time"])])

                machine_parameter_names = self.new_alerts[["L1Name", "parameters"]].to_numpy().tolist()

                # group_details, axis_details = get_axis_group_details_pony(machine_parameter_names)
                #
                # self.new_alerts["Parameter"] = self.new_alerts["parameters"]
                # self.new_alerts["Axis"] = self.new_alerts["parameters"]
                # self.new_alerts["Parameter"] = self.new_alerts["Parameter"].map(group_details)
                # self.new_alerts["Axis"] = self.new_alerts["Axis"].map(axis_details)

                self.new_alerts = self.new_alerts.drop(columns=["condition", "parameters"])

                if "warning_limit" in self.new_alerts.columns:
                    self.new_alerts = self.new_alerts[["L1Name", "updatedate", "Parameter", "Axis",
                                                       "value", "warning_limit", "critical_limit"]]
                else:
                    self.new_alerts = self.new_alerts[["L1Name", "updatedate", "Parameter", "Axis", "value"]]

            else:
                # If both alerts are empty, we set the new alerts to None
                self.new_alerts = None
        except Exception as error:
            LOGGER.exception(f"Error while checking for new anomaly: {error}")
            raise CheckAnomalyParametersGroupClassFailure(error)

    def send_alerts(self):

        try:

            # If no new data is available, we skip the remaining code
            if self.recent_critical_data is None:
                LOGGER.debug("No New Data")
                return

            # If no new alerts is available, we skip the remaining code
            if self.new_alerts is None:
                LOGGER.debug("No New Alerts")
                return

            LOGGER.debug("NEW ALERTS COMBINED")
            LOGGER.debug(self.new_alerts.head())

            report_file_name = EMAIL_REPORT_ROOT_DIRECTORY + f"alert_report_{self.group_name}_{int(time.time())}.xlsx"

            report_file_name_temp = EMAIL_REPORT_ROOT_DIRECTORY_TEMP + f"alert_report_{self.group_name}" \
                                                                       f"_{int(time.time())}.xlsx"
            LOGGER.debug(report_file_name)
            # self.new_alerts.to_excel(report_file_name)
            # self.new_alerts.to_excel(report_file_name_temp)

            alert_data = self.new_alerts.to_numpy().tolist()
            alert_data_with_index = []

            for row_index, row_data in enumerate(alert_data):
                current_row = [row_index + 1, row_data[0], str(row_data[1] + datetime.timedelta(hours=5, minutes=30))]
                current_row.extend(row_data[2:])
                # empty_data.append([i+1].extend(d))
                alert_data_with_index.append(current_row)

            # alert_data = [[i+1].extend(d) for i, d in enumerate(alert_data)]

            if self.group_name == "DYNAMIC_PARAMETERS":

                file_location = EMAIL_REPORT_ROOT_DIRECTORY + "critical_alert_report_dynamic.xlsx"

                create_excel_report(file_location=file_location, data=alert_data_with_index,
                                    parameter_type="dynamic")
            else:

                file_location = EMAIL_REPORT_ROOT_DIRECTORY + "critical_alert_report_static.xlsx"
                create_excel_report(file_location=file_location, data=alert_data_with_index)

            # Adding Content and sending it
            # EMAIL_SERVER.send(RECEIVER_EMAIL, email_subject, email_body, attachments=[report_file_name])
        except Exception as error:
            LOGGER.exception(f"Error While sending reports: {error}")
            raise SendAnomalyParametersGroupClassFailure


class DynamicParameters(ParametersGroupBase):
    """

    This represents the base class for all parameters group

    """

    def __init__(self, latest_update_time=datetime.datetime.utcfromtimestamp(1648205580),
                 group_name="dynamic_parameters", mongodb_query="", *args, **kwargs):

        # This list represents the regex patterns used to get the 4 specific
        super().__init__(group_name, mongodb_query, latest_update_time, *args, **kwargs)
        self.regex_dynamic_param = None

    def get_new_data(self):

        try:
            LOGGER.debug("*" * 30)
            program_history = get_program_history(self.latest_update_time)
            LOGGER.debug(f"The current latest time: {self.latest_update_time}")

            if not program_history:
                self.recent_data = None
                return

            program_early_start = program_history[0]["updatedate"]
            program_early_end = program_history[0]["enddate"]
            program_latest_start = program_history[-1]["updatedate"]
            program_latest_end = program_history[-1]["enddate"]

            LOGGER.info(f"The program earliest start time: {program_early_start} and endtime: {program_early_end}")
            LOGGER.info(f"The program Latest start time: {program_latest_start} and "
                         f"the program end: {program_latest_end}")

            # self._temp_latest_update_time = datetime.datetime(2022, 6, 20, 15, 15, 0, tzinfo=timezone.utc)
            next_update_time = program_history[-1]["enddate"]
            next_update_time = next_update_time.replace(tzinfo=timezone.utc)
            self._temp_latest_update_time = next_update_time

            all_data = []
            LOGGER.info(f"Number of programs: {len(program_history)}")
            # input("Enter something")

            for program in program_history:
                LOGGER.debug("^" * 10)
                # machine_name = "T_H_OP180A"

                machine_name = program["L1Name"]
                parameters = set(get_spindle_servo_params_mongo(machine_name))
                variant_path = program["mainprog"]

                # self.regex_dynamic_param = [rf"servoload_{i}_(?i)" for i in range(number_of_parameters - 1)]
                # self.regex_dynamic_param.append(r"spindleload(?i)")

                search_start_time = program["updatedate"]
                search_start_time = search_start_time.replace(tzinfo=timezone.utc)
                # search_start_time = datetime.datetime(2022, 6, 17, 10, 55, 0, tzinfo=timezone.utc)

                search_end_time = program["enddate"]
                search_end_time = search_end_time.replace(tzinfo=timezone.utc)
                # search_end_time = datetime.datetime(2022, 6, 20, 15, 15, 0, tzinfo=timezone.utc)

                LOGGER.debug(f"Current program  start_time {search_start_time} and end_time {search_end_time}")
                # input("before all parameters")
                for parameter in parameters:
                    LOGGER.debug("#" * 5)

                    # Getting the mongodb client, that talks to L1Signal_Pool_Active
                    collector = get_collector(collection="L1Signal_Pool")

                    # Getting the mongodb query parameter
                    pipeline = get_dynamic_data_template(machine_name=machine_name, regex_pattern=parameter,
                                                         search_start_time=search_start_time,
                                                         search_end_time=search_end_time
                                                         )

                    data = list(collector.aggregate(pipeline))

                    # LOGGER.debug(len(data))
                    # If data is available
                    if data:
                        # We set the recent_data variable to a pandas dataframe with values equal to the query result
                        recent_data = pd.DataFrame(data)
                        LOGGER.info(f"First Time for the current program and selected"
                                     f" parameter: {recent_data.iloc[0, :]}")
                        LOGGER.info(f"Last Time for the current program and selected"
                                     f" parameter: {recent_data.iloc[-1, :]}")

                        # We need to set the latest update time only after the insertion of data into timescaledb,
                        # Because if database insertion operation fails, then we need to again query those data from
                        # Mongodb and then insert ,hence only after successfully insertion we should update this
                        # Check in the insert_to_timescaledb method

                        # We set the latest_update_time equal to the latest (max of updatedate)
                        # Timestamp of any recorded Signal, we take the last from the dataframe, since the data
                        # is already sorted in ascending order
                        # self.latest_update_time = self.recent_data.iat[-1, 1].to_pydatetime()
                        # LOGGER.debug(self.latest_update_time)

                        # The result from MtLinki will have only the signalname, this has to be converted to the actual
                        # id of the parameter (to be) stored in the timescaledb, in table "machine_parameters"
                        # Hence, getting the ids for all signalname.
                        parameter_id_mapping = get_parameters_id_timescaledb()

                        # Creating a new column in the df called "parameters and setting it
                        # Equal to the signalname column
                        recent_data["parameters"] = recent_data["signalname"]

                        # Mapping all the signalname to id column of the table "machine_parameters "
                        # (such as 44 for ApcBatLow_0_path1_T_B_OP160)
                        recent_data["signalname"] = recent_data["signalname"].map(parameter_id_mapping)
                        # LOGGER.debug(recent_data.head())

                        parameter_id = recent_data["signalname"].iloc[0]
                        # condition = self.check_dynamic_condition_variant(parameter_id, variant_path,
                        #                                                  recent_data["value"].to_list())
                        condition = 1

                        # We create new column called condition equal to the value returned from check_condition
                        # Only for the last row, everything else is set to null
                        recent_data["condition"] = None
                        recent_data.iloc[-1, recent_data.columns.get_loc("condition")] = condition

                        # LOGGER.debug(recent_data.head())
                        all_data.append(recent_data)

            # We do the following only if there is any data for each for the parameters
            if all_data:
                # Concatenate all list values to pandas dataframe in self.recent_data
                self.recent_data = pd.concat(all_data)
                self.recent_data["updatedate"] = self.recent_data["updatedate"].apply(
                    lambda dt: dt.replace(tzinfo=timezone.utc))
                LOGGER.debug("Concatenated all data")
            else:
                self.recent_data = None

        except ServerSelectionTimeoutError as error:
            LOGGER.exception(f"Unable to select mongodb server with following error: {error.args[0]}")
            self.recent_data = None
            raise MtLinkiGetNewDataParametersGroupClassFailure("error from 'get_new_data")
        except ConnectionFailure as error:
            LOGGER.exception(f"Unable to make connection to database server with following error: {error.args[0]}")
            self.recent_data = None
            raise MtLinkiGetNewDataParametersGroupClassFailure("error from 'get_new_data")
        except NetworkTimeout as error:
            LOGGER.exception(f"Network timed out while connecting to database server with"
                             f" following error: {error.args[0]}")
            self.recent_data = None
            raise MtLinkiGetNewDataParametersGroupClassFailure("error from 'get_new_data")
        except OperationFailure as error:
            LOGGER.exception(f"The database operation failed with following error: {error.args[0]}")
            self.recent_data = None
            raise MtLinkiGetNewDataParametersGroupClassFailure("error from 'get_new_data")
        except ParameterIdQueryFailure as error:
            LOGGER.exception(f"Couldn't get the parameters id from the timescaledb due to "
                             f"following error: {error.args[0]}")
            self.recent_data = None
            raise MtLinkiGetNewDataParametersGroupClassFailure("error from 'get_new_data")
        except Exception as error:
            LOGGER.exception(f"error {error.args[0]}")
            self.recent_data = None
            raise MtLinkiGetNewDataParametersGroupClassFailure("error from 'get_new_data")

    @staticmethod
    def check_dynamic_condition(parameter_id, data):
        """

        This method checks the condition of a given (dynamic) parameter by using kruskal hypothesis testing

        :param parameter_id: The parameter whose condition needs to be checked
        :type parameter_id: int

        :param data: The current cycle's data for the given parameter
        :type data: list

        :return: The condition id
        :rtype: int

        """

        reference_signal = get_reference_signal(parameter_id)

        try:
            if reference_signal:
                condition = kruskal_test(reference_signal, data)
                return condition
        except Exception as error:
            return 1

        return 1

    @staticmethod
    def check_dynamic_condition_variant(parameter_id, variant_path, data):
        """

        This method checks the condition of a given (dynamic) parameter by using kruskal hypothesis testing

        :param parameter_id: The parameter whose condition needs to be checked
        :type parameter_id: int

        :param data: The current cycle's data for the given parameter
        :type data: list

        :return: The condition id
        :rtype: int

        """

        reference_signal, alpha_value = get_reference_signal_variants(parameter_id, variant_path)

        if reference_signal:
            condition = kruskal_test(reference_signal, data, alpha_value)
            return condition

        return 1


class CollectorClass:
    """

    Main Class to represent the Collector System for static parameters

    """

    def __init__(self, read_cycle_time):
        """

        INITIALIZATION
        ==================

        :param read_cycle_time: The rate at which the MtLinki should be queried for new data (eg 5sec)
        :type read_cycle_time: int

        """

        self.read_cycle_time = read_cycle_time

        # The attribute that will store all the parameter groups (in a list in the load_parameters method)
        self.static_parameters = None

        self.dynamic_parameters = None

        # The attribute that will store all the combined alerts (as dataframe, later) for all parameters
        #  During the current read cycle
        self.combined_alerts = None

    def load_parameters(self):
        """

        Method to load the parameters details from the configuration files and create ParametersGroupBase class

        :return: Nothing
        :rtype: None

        """

        try:

            # config_data = load_config_data(self.parameters_config_file)
            config_data = get_static_config()

            if config_data:
                self.static_parameters = [ParametersGroupBase(*data) for data in config_data]
            else:
                raise LoadParamCollectorClassFailure("No data available for static parameters")

        except LoadConfigFailure as error:
            LOGGER.exception(f"Error while loading the parameters: {error.args[0]}")
            raise LoadParamCollectorClassFailure("Error from load_parameters")
        except Exception as error:
            LOGGER.exception(f"Error while loading the parameters: {error.args[0]}")
            raise LoadParamCollectorClassFailure("Error from load_parameters")

    def do_workflow(self):
        """

        Method that represents one unit of workflow, where all the parameter of this system will be
        queried for new data, added new condition column, insert that data into timescaledb, check for new anomaly

        :return: Nothing
        :rtype: None

        """

        try:
            start_time = time.time()
            for parameter in self.static_parameters:
                # The following order has to be followed, else condition monitoring will not happen
                # 1
                parameter.get_new_data()
                # 2
                parameter.add_condition_columns()
                # 3
                parameter.insert_to_timescaledb()

                # 4
                parameter.check_activity()

                # 5
                parameter.insert_new_activity()

                # 6
                parameter.update_existing_activity()

                # 7
                # parameter.check_for_new_anomaly()

                # 8
                # parameter.send_alerts()

            LOGGER.info(f"Total Time Taken: {time.time() - start_time}")
        except MtLinkiGetNewDataParametersGroupClassFailure as error:
            LOGGER.exception(f"Error while doing workflow, While Getting new data: {error.args[0]}")
            raise WorkflowCollectorClassFailure("Error from load_parameters")
        except AddConditionColumnParametersGroupClassFailure as error:
            LOGGER.exception(f"Error while doing workflow, While Adding columns data: {error.args[0]}")
            raise WorkflowCollectorClassFailure("Error from load_parameters")
        except InsertTimescaleParametersGroupClassFailure as error:
            LOGGER.exception(f"Error while doing workflow, while inserting into timescale db: {error.args[0]}")
            raise WorkflowCollectorClassFailure("Error from load_parameters")
        except CheckAnomalyParametersGroupClassFailure as error:
            LOGGER.exception(f"Error while doing workflow, while checking for anomaly: {error.args[0]}")
            raise WorkflowCollectorClassFailure("Error from load_parameters")
        except Exception as error:
            LOGGER.exception(f"Error while doing workflow: {error.args[0]}")
            raise WorkflowCollectorClassFailure("Error from load_parameters")

    def merge_alerts(self):
        """

        Method to merge all the alerts from each individual parameter (alerts)

        :return: Nothing
        :rtype: None

        """

        try:
            start_time = time.time()

            self.combined_alerts = []
            for parameter in self.static_parameters:

                # If the parameter doesnt have any new recent data, we skip the rest of the code
                if parameter.recent_data is None:
                    continue

                # If the parameter doesnt have any new alerts, we skip the rest of the code
                if parameter.new_alerts is None:
                    continue

                # If the parameter has new alerts, we append it to the list
                self.combined_alerts.append(parameter.new_alerts)

            # If in case the combined_alerts is empty, we set it to None
            if not self.combined_alerts:
                print("INSIDE COMBINED ALERTS")
                self.combined_alerts = None
                return

            # We the combined alerts is not empty we create a dataframe by combining all the list elements
            self.combined_alerts = pd.concat(self.combined_alerts)

            # Resetting the index of new dataframe
            self.combined_alerts.reset_index(inplace=True, drop=True)
            LOGGER.info(f"Total Time Taken: {time.time() - start_time}")
        except Exception as error:
            LOGGER.exception(f"Error while merging alerts: {error.args[0]}")
            self.combined_alerts = None
            raise MergeAlertsCollectorClassFailure("Error from 'merge_alerts'")

    def send_combined_alerts(self):
        """
        Method to notify all the combined alerts via email

        :return: Nothing
        :rtype: None
        """

        try:

            # If no new alerts is available, we skip the remaining code
            if self.combined_alerts is None:
                LOGGER.debug("No New Alerts")
                return

            LOGGER.debug("NEW ALERTS COMBINED")
            LOGGER.debug(self.combined_alerts.head())

            report_file_name = EMAIL_REPORT_ROOT_DIRECTORY + f"static_alert_report_{int(time.time())}.xlsx"
            report_file_name_temp = EMAIL_REPORT_ROOT_DIRECTORY_TEMP + f"static_alert_report_{int(time.time())}.xlsx"
            LOGGER.debug(report_file_name)
            self.combined_alerts.to_excel(report_file_name)
            self.combined_alerts.to_excel(report_file_name_temp)

            alert_data = self.combined_alerts.to_numpy().tolist()
            alert_data_with_index = []

            for row_index, row_data in enumerate(alert_data):
                current_row = [row_index + 1, row_data[0], str(row_data[1] + datetime.timedelta(hours=5, minutes=30))]
                current_row.extend(row_data[2:])
                # empty_data.append([i+1].extend(d))
                alert_data_with_index.append(current_row)

            # alert_data = [[i+1].extend(d) for i, d in enumerate(alert_data)]

            if self.group_name == "DYNAMIC_PARAMETERS":

                file_location = EMAIL_REPORT_ROOT_DIRECTORY + "critical_alert_report_dynamic.xlsx"

                create_excel_report(file_location=file_location, data=alert_data_with_index,
                                    parameter_type="dynamic")
            else:

                file_location = EMAIL_REPORT_ROOT_DIRECTORY + "critical_alert_report_static.xlsx"
                create_excel_report(file_location=file_location, data=alert_data_with_index)

            # email_subject = "MACHINE CONDITION ALERTS"
            # email_body = "New Alerts Generated"
            # LOGGER.info("SENDING EMAIL")
            # # Adding Content and sending it
            # # EMAIL_SERVER.send(RECEIVER_EMAIL, email_subject, email_body, attachments=[report_file_name])
            # LOGGER.info("SENT SUCCESSFULLY")
        except Exception as error:
            LOGGER.exception(f"Error while sending combined alerts: {error.args[0]}")
            raise SendAlertsCollectorClassFailure("Error from 'send_combined_alerts'")

    def start_collector(self):
        """

        Method to start the collector system, this will loop for ever with a sleep time equal to read_cycle_time

        :return: Nothing
        :rtype: None

        """

        LOGGER.info("STARTING COLLECTOR")

        while True:

            try:
                # Do one unit of workflow
                self.do_workflow()

                # Merge all parameters alerts
                # self.merge_alerts()

                # Send all combined alerts
                # self.send_combined_alerts()

                LOGGER.info(f"SLEEPING FOR {self.read_cycle_time} SECONDS")
                time.sleep(self.read_cycle_time)
                LOGGER.info("WOKE UP")
            except WorkflowCollectorClassFailure as error:
                LOGGER.exception(f"Error While doing the workflow: {error.args[0]}")
                sys.exit(-1)
            except MergeAlertsCollectorClassFailure as error:
                LOGGER.exception(f"Error While Merging alerts: {error.args[0]}")
                sys.exit(-1)
            except SendAlertsCollectorClassFailure as error:
                LOGGER.exception(f"Error While sending alerts: {error.args[0]}")
                sys.exit(-1)
            except Exception as error:
                LOGGER.exception(f"Unknown Error While doing the workflow: {error.args[0]}")
                sys.exit(-1)


class DynamicCollectorClass(CollectorClass):
    """

    Main Class to represent the Collector System for Dynamic parameters

    """

    def load_parameters(self):
        """

        Method to load the parameters details from the configuration files and create ParametersGroupBase class

        :return: Nothing
        :rtype: None

        """

        try:

            # Getting the configuration details for dynamic parameters
            dynamic_config_file = get_dynamic_config()

            future_dynamic_time = datetime.datetime.now(timezone.utc) + datetime.timedelta(minutes=1)
            # future_dynamic_time = datetime.datetime(2024, 3, 9, 7,
            #                                         50, 0, tzinfo=timezone.utc)
            LOGGER.debug(f"The Dynamic Collector Start Time is: {future_dynamic_time}")

            # Creating DynamicParameters class
            self.dynamic_parameters = DynamicParameters(group_name=dynamic_config_file[0],
                                                        mongodb_query=dynamic_config_file[1],
                                                        latest_update_time=future_dynamic_time)

        except LoadConfigFailure as error:
            LOGGER.exception(f"Error while loading the parameters: {error.args[0]}")
            raise LoadParamCollectorClassFailure("Error from load_parameters")
        except Exception as error:
            LOGGER.exception(f"Error while loading the parameters: {error.args[0]}")
            raise LoadParamCollectorClassFailure("Error from load_parameters")

    def do_workflow(self):
        """

        Method that represents one unit of workflow, where the dynamic parameters of this system will be
        queried for new data, added new condition column, insert that data into timescaledb, check for new anomaly

        :return: Nothing
        :rtype: None

        """

        try:
            start_time = time.time()

            self.dynamic_parameters.get_new_data()
            self.dynamic_parameters.insert_to_timescaledb()
            #self.dynamic_parameters.check_for_new_anomaly()
            #self.dynamic_parameters.send_alerts()

            LOGGER.debug(f"Total Time Taken: {time.time() - start_time}")

        except MtLinkiGetNewDataParametersGroupClassFailure as error:
            LOGGER.exception(f"Error while doing workflow, While Getting new data: {error.args[0]}")
            raise WorkflowCollectorClassFailure("Error from load_parameters")
        except AddConditionColumnParametersGroupClassFailure as error:
            LOGGER.exception(f"Error while doing workflow, While Adding columns data: {error.args[0]}")
            raise WorkflowCollectorClassFailure("Error from load_parameters")
        except InsertTimescaleParametersGroupClassFailure as error:
            LOGGER.exception(f"Error while doing workflow, while inserting into timescale db: {error.args[0]}")
            raise WorkflowCollectorClassFailure("Error from load_parameters")
        except CheckAnomalyParametersGroupClassFailure as error:
            LOGGER.exception(f"Error while doing workflow, while checking for anomaly: {error.args[0]}")
            raise WorkflowCollectorClassFailure("Error from load_parameters")
        except Exception as error:
            LOGGER.exception(f"Error while doing workflow: {error.args[0]}")
            raise WorkflowCollectorClassFailure("Error from load_parameters")

    def start_collector(self):
        """

        Method to start the collector system, this will loop for ever with a sleep time equal to read_cycle_time

        :return: Nothing
        :rtype: None

        """

        LOGGER.info("STARTING DYNAMIC COLLECTOR")

        while True:

            try:
                # Do one unit of workflow
                self.do_workflow()

                LOGGER.debug(f"SLEEPING FOR {self.read_cycle_time} SECONDS")
                # time.sleep(self.read_cycle_time)
                LOGGER.debug("WOKE UP")
            except WorkflowCollectorClassFailure as error:
                LOGGER.exception(f"Error While doing the workflow: {error.args[0]}")
            except MergeAlertsCollectorClassFailure as error:
                LOGGER.exception(f"Error While Merging alerts: {error.args[0]}")
            except SendAlertsCollectorClassFailure as error:
                LOGGER.exception(f"Error While sending alerts: {error.args[0]}")
            except Exception as error:
                LOGGER.exception(f"Unknown Error While doing the workflow: {error.args[0]}")


def main():
    """
    Main Function
    ====================
    
    Main function to call appropriate functions to start the collector system

    """

    # Create anew CollectorClass
    # collector_system = CollectorClass(read_cycle_time=5)
    collector_system = DynamicCollectorClass(read_cycle_time=5)

    # Load the parameters
    collector_system.load_parameters()

    # Start the collector system
    collector_system.start_collector()

    # UTC TIME EPOCH FOR Date and time GMT: Wednesday, 22 June 2022 04:58:37 = 1655873917
    # UTC TIME EPOCH FOR Date and time (GMT): Wednesday, 22 June 2022 06:37:13 = 1655879833

    # dp = DynamicParameters()
    # dp.get_new_data()
    # dp.insert_to_timescaledb()
    # dp.check_for_new_anomaly()


if __name__ == '__main__':
    main()
