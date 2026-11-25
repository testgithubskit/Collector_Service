#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
DATABASE CRUD OPERATIONS
================================

Module consisting of functions to carry out database crud operations

This script requires the following modules be installed in the python environment

    Standard Library
    =================
    * logging - To perform logging operations.
    * pprint - To pretty print the output from database operations.

    Related 3rd Party Library
    =============================

This script contains the following function
    * get_current_machine_data - Function that connects to database to get the current machine details
"""

# Standard library imports
import logging
import pprint
import time
from datetime import datetime, timedelta
import pytz
from typing import Optional
import calendar
import math

# Related third party imports
from pony.orm import db_session, desc, commit, count as pony_count, select
from pony.orm.core import ObjectNotFound

# Local application/library specific imports
from machine_monitoring_app.database.pony_models import Machine, ParameterGroup, MachineParameter, \
    RealTimeParameter, User as UserPony, SparePart, EmailUser, MachinePartCount

from machine_monitoring_app.exception_handling.custom_exceptions import NoParameterGroupError, \
    GetParamGroupDBError, GetAllParameterDBError, GetMachineTimelineError

from machine_monitoring_app.models.base_data_models import UserInDB, User as UserPydantic
from machine_monitoring_app.database.mongodb_client import get_mongo_collection

from machine_monitoring_app.database.mongo_db_utils import get_exceed_group_template, get_within_group_template, \
    get_between_head_group_template, get_between_tail_group_template, get_exceed_group_day_template, \
    get_within_group_day_template, get_between_head_group_day_template, get_between_tail_group_day_template, \
    get_timeline_group_template, get_timespan_group_template, get_count_group_template

from machine_monitoring_app.models.response_models import SparePart as PydanticSparePart
from machine_monitoring_app.database.db_utils import get_all_status_templates, get_all_recent_time_template
from machine_monitoring_app.database.db_utils import PONY_DATABASE

__author__ = "smt18m005@iiitdm.ac.in"

LOGGER = logging.getLogger(__name__)


@db_session(optimistic=False)
def get_current_machine_data(parameter_group_id=5):
    """

    Retrieves the current machine details from the database

    :param parameter_group_id: The parameter group identifier
    :type parameter_group_id: int

    :return: The current machine details
    :rtype: dict

    """

    try:
        # Selecting the given parameter_group_id
        parameter_group = ParameterGroup[parameter_group_id]

        response_data = {"param_actual_name": parameter_group.group_name, "param": parameter_group.id, "machines": [],
                         "params_group_status": []}

        LOGGER.info("Retrieving current machine details")

        response_data["machines"] = get_parameter_group_status(parameter_group)

        response_data["params_group_status"] = get_all_parameter_group_status()

        return response_data
    except ObjectNotFound as error:
        LOGGER.error(f"The given parameter group id is not available: {error.args[0]}")
        raise NoParameterGroupError


@db_session(optimistic=False)
def get_parameter_group_status(parameter_group):
    """

    Function to get the parameter group status for given parameter group id

    :param parameter_group: The parameter group object
    :type parameter_group: ParameterGroup

    :return: List of machines and their parameter status
    :rtype: list

    """

    try:
        start_time = time.time()

        parameter_status = []

        # Selecting all the machines available in the database
        machines = Machine.select(lambda current_machine: current_machine.id > 1)

        # For all the machines, we do the following
        for machine in machines:
            # The current machine's data are
            current_machine_data = {"name": machine.name, "axes": []}

            # Query to get all the axes for the current machine
            axes = MachineParameter.select(lambda parameter: parameter.machine.id == machine.id)
            axes = axes.filter(lambda parameter: parameter.parameter_group.id == parameter_group.id). \
                order_by(MachineParameter.name)

            axes = list(axes)

            # For each axis
            for count, axis in enumerate(axes):

                if (parameter_group.id != 15) and (parameter_group.id != 16):
                    axis_count = count
                else:
                    if count == 0:
                        continue
                    else:
                        axis_count = count - 1

                # Set the base current axis data, as per the response model
                current_axis_data = {"name": axis_count, "actual_name": axis.name}

                # Get the real time parameter, equal to the current axis
                current_value_base_query = RealTimeParameter. \
                    select(lambda parameter: parameter.machine_parameter.id == axis.id)

                current_value = list(current_value_base_query.
                                     order_by(desc(RealTimeParameter.time)).for_update()[:1])

                if not current_value:

                    # If in case this is the "RADIATOR_FAN1_SERVO_SPINDLE_AMPLIFIER" group, then
                    # We need to check the first parameter (spindle parameter)
                    if (parameter_group.id == 15) or (parameter_group.id == 16):

                        # Set the base current axis data, as per the response model
                        current_axis_data = {"name": axis_count, "actual_name": axes[0].name}

                        # Get the real time parameter, equal to the current axis
                        current_value_base_query = RealTimeParameter. \
                            select(lambda parameter: parameter.machine_parameter.id == axes[0].id)

                        current_value = list(current_value_base_query.
                                             order_by(desc(RealTimeParameter.time)).for_update()[:1])

                        if not current_value:
                            # If there is no data for the spindle parameter for current machine, we break
                            # This will be the case only for testing, in actual you will have data
                            break

                        current_value = current_value[0]

                        if current_value.parameter_condition.id == 1:
                            # If the condition is OK, we skip the remaining code
                            break

                        # Set the current data axis data keys
                        current_axis_data["value"] = current_value.value
                        current_axis_data["status"] = current_value.parameter_condition.id
                        current_axis_data["last_update_time"] = current_value.time.timestamp()

                        # Append to the current machine details
                        current_machine_data["axes"].append(current_axis_data)

                    # If the data is not available it means we we were accessing an axis data for which data is
                    # Is not available, then we will skip remaining of the code since they are not configured
                    break

                current_value = current_value[0]

                if current_value.parameter_condition.id == 1:
                    # If the condition is OK, we skip the remaining code
                    continue

                # # Filter only non_ok data
                # current_value = current_value_base_query.filter(lambda parameter: parameter.parameter_condition.id > 1)
                #
                # # Sort by time (descending order) and limit to 1 (which gives the recent most data)
                # # Making it for update query, so that we don't get the Unrepeatable Read Problem
                # current_value = current_value.order_by(desc(RealTimeParameter.time)).for_update()[:1]

                # Set the current data axis data keys
                current_axis_data["value"] = current_value.value
                current_axis_data["status"] = current_value.parameter_condition.id
                current_axis_data["last_update_time"] = current_value.time.timestamp()

                # Append to the current machine details
                current_machine_data["axes"].append(current_axis_data)

            if current_machine_data["axes"]:

                # Since this machine had a non_ok data, we initially set the status to 2 (warning)
                current_machine_data["status"] = 2

                # loop through all the machine's axis data
                for axis in current_machine_data["axes"]:
                    # If the status of the axis is 3
                    if axis["status"] == 3:
                        # Set the machine status to 3 and break from the loop
                        current_machine_data["status"] = 3
                        break
                # If any parameter(axes) was there with non_ok data, append it to all parameter_status list
                parameter_status.append(current_machine_data)

        LOGGER.info("time for individual parameter group")
        LOGGER.info(time.time() - start_time)

        return parameter_status
    except Exception as error:
        LOGGER.exception(f"Exception while processing status of machine for given parameter group: {error.args[0]}")
        raise GetParamGroupDBError


@db_session(optimistic=False)
def get_all_parameter_group_status():
    """

    Function used to return status of all parameter group

    :return: Status of all parameter groups
    :rtype: list

    """

    try:
        start_time = time.time()

        status = [1 for _ in range(17)]
        query_template = get_all_status_templates()

        # Using a really complicated group by function along with timescale db inbuilt function
        # To get the total number of warning and critical parameters
        warning_data = list(PONY_DATABASE.select(query_template.format(condition_holder=2)))
        critical_data = list(PONY_DATABASE.select(query_template.format(condition_holder=3)))
        # If we have any parameter in warning state, we do the following
        if warning_data:
            # For all the warning parameter
            for data in warning_data:
                # The first value of the list given the parameter group id from the actual table
                # Hence APC Battery would be 1, but in the status list the index would be 0
                # Hence we need to subtract 1 from it
                status[data[0] - 1] = 2

        if critical_data:
            for data in critical_data:
                # The first value of the list given the parameter group id from the actual table
                # Hence APC Battery would be 1, but in the status list the index would be 0
                # Hence we need to subtract 1 from it
                status[data[0] - 1] = 3

        # For all the exiting parameter group, do the following
        # for group in ParameterGroup.select().sort_by(ParameterGroup.id):
        #
        #     # Get the parameters,that belongs to the current parameter group
        #     parameters = MachineParameter.select(lambda parameter: parameter.parameter_group.id == group.id)
        #
        #     critical_true_status = False
        #     warning_true_status = False
        #
        #     for parameter_id in parameters:
        #         recent_data = RealTimeParameter.\
        #             select(lambda real_parameter: real_parameter.machine_parameter == parameter_id)
        #
        #         # recent_data = recent_data.order_by(desc(RealTimeParameter.time)).for_update()[:1]
        #         recent_data = list(recent_data.order_by(desc(RealTimeParameter.time))[:1])
        #
        #         if not recent_data:
        #             continue
        #
        #         recent_data = recent_data[0]
        #         recent_data_condition = recent_data.parameter_condition.id
        #
        #         if recent_data_condition == 3:
        #             status.append(3)
        #             critical_true_status = True
        #             break
        #         elif recent_data_condition == 2:
        #             warning_true_status = True
        #
        #     if not critical_true_status:
        #         if warning_true_status:
        #             status.append(2)
        #         else:
        #             status.append(1)

        # Query the real_time_data for the parameters belonging to current parameter group
        # real_time_data = RealTimeParameter.select(lambda parameter: parameter.machine_parameter in list(
        # parameters))

        # Filter out only the non ok data
        # real_time_data_non_ok = real_time_data.filter(lambda parameter: parameter.parameter_condition.id > 1)[:]

        # If any non ok data is available
        # if real_time_data_non_ok:
        #     # Find the data that are in critical condition
        #     real_time_data_critical = real_time_data.filter(lambda parameter: parameter.parameter_condition.id > 2)[
        #                               :]
        #
        #     # If critical condition exist, append 3 to the status list
        #     if real_time_data_critical:
        #         status.append(3)
        #     else:
        #         # Else append 2
        #         status.append(2)
        # else:
        #     # If no non_ok data was found everything was ok, hence set the status to 1
        #     status.append(1)

        LOGGER.info("time for all status")
        print("time for all status")
        LOGGER.info(time.time() - start_time)
        print(time.time() - start_time)
        print(status)

        return status
    except Exception as error:
        LOGGER.exception(f"Exception while processing status of machine for given parameter group: {error.args[0]}")
        raise GetAllParameterDBError


@db_session(optimistic=False)
def get_machine_timeline(machine_name, parameter_group_id=5, axis_id=0, start_time=1655859600, end_time=1655874000):
    """

    Retrieves the current machine's given parameter group and axis's full timeline information for given
    start and end time

    :param machine_name: The machine name whose data is required
    :type machine_name: str

    :param parameter_group_id: The parameter group identifier
    :type parameter_group_id: int

    :param axis_id: The parameter axis identifier
    :type axis_id: int

    :param start_time: Start time for which the data needs to be queried in epoch format
    :type start_time: float

    :param end_time: End time for which the data needs to be queried in epoch format
    :type end_time: float

    :return: The current machine's full timeline information
    :rtype: dict

    """

    try:
        # Getting all the parameters for the given machine in the given parameter group
        machine_parameters = get_parameters(machine=machine_name, parameter_group_id=parameter_group_id)

        LOGGER.info(f"Requested parameters all:{machine_parameters}")

        if not machine_parameters:
            # If there was not data found, raise error
            raise GetMachineTimelineError("Invalid machine/ parameter identifier")

        if axis_id >= len(machine_parameters):
            # If the given axis_id is greater than than the total number of axes for the machine, raise error
            raise GetMachineTimelineError("Invalid axis identifier")

        # Get the actual parameter name
        requested_parameter_id = machine_parameters[axis_id]

        requested_parameter_object = MachineParameter[requested_parameter_id]

        LOGGER.info(f"Requested parameter:{requested_parameter_id}")

        # Getting real time data
        real_time_data = get_realtime_data(requested_parameter_id, start_time, end_time)

        # If not data available for the given time, we set the real time data to be
        # Equal to data from recent most time to one hour before it.
        if not real_time_data:
            # We get the timestamp of the recent most recorded value of the requested parameter id
            recent_end_time = get_recent_time_parameter(requested_parameter_id)

            # We add 5 hour and 30 minutes to adjust for gmt timezone
            recent_end_time = recent_end_time + 19800
            #recent_end_time = recent_end_time

            # We set the stating time stamp for the search to be one hour before the recent most time
            recent_start_time = recent_end_time - 3600

            # If there is any data available for the given parameter (recent most data)
            # We set the real time data to be the data between the recent most recorded value and one hour before it
            if recent_end_time:
                real_time_data = get_realtime_data(requested_parameter_id, recent_start_time, recent_end_time)

        # Do the following only if real time data is available (either for the requested timestamp or
        # The timestamp of recent most value and one hour before it)
        if real_time_data:
            # Creating response dictionary
            # If warning limit is none, it means it is a dynamic parameter ,
            # And we set the limits to zero for them
            if (requested_parameter_object.warning_limit is not None) and \
                    not math.isnan(requested_parameter_object.warning_limit):

                print("value: ", type(requested_parameter_object.warning_limit))

                response_data = {"param": parameter_group_id, "machine": machine_name, "axis": axis_id,
                                 "start_time": real_time_data[0][0], "stop_time": real_time_data[0][-1],
                                 "data": real_time_data[1],
                                 "timestamps": real_time_data[0],
                                 "warning_limit": requested_parameter_object.warning_limit,
                                 "critical_limit": requested_parameter_object.critical_limit}
            else:

                response_data = {"param": parameter_group_id, "machine": machine_name, "axis": axis_id,
                                 "start_time": real_time_data[0][0], "stop_time": real_time_data[0][-1],
                                 "data": real_time_data[1],
                                 "timestamps": real_time_data[0],
                                 "warning_limit": 0,
                                 "critical_limit": 0}

            return response_data

    except ObjectNotFound as error:
        LOGGER.error(f"The object not found in database: {error.args[0]}")
        raise GetMachineTimelineError
    except Exception as error:
        LOGGER.error(f"The issues with database: {error.args[0]}")
        raise GetMachineTimelineError(error.args[0])


@db_session
def get_parameters(machine="T_B_OP160", parameter_group_id=1):
    """

    Function to get all parameters for a given machine in a given parameter group (identifier)

    :param machine: The machine for which the parameters are required
    :type machine: str

    :param parameter_group_id: The parameter group identifier
    :type parameter_group_id: int

    :return: List of sorted (by name) parameter (identifier) for the given machine and parameter group
    :rtype: list

    """

    try:
        LOGGER.info(f"Getting all parameters for machine: {machine} and group id: {parameter_group_id}")

        # Selecting machine parameters based on given machine name and parameter group identifier
        parameters = MachineParameter.select(lambda parameter: parameter.machine.name == machine)
        parameters = parameters.filter(lambda parameter: parameter.parameter_group.id == parameter_group_id)

        # Sorting by machine parameter name (hence ApcBatLow_0, ApcBatLow_1, ...so on will be the order of results
        # returned)
        parameters = parameters.sort_by(MachineParameter.name)

        # If the query results in any data, do the following
        if parameters:
            LOGGER.info("parameter available")
            # Return only the parameter ids
            return [param.id for param in parameters]
    except Exception as error:
        LOGGER.exception(f"Exception while processing status of machine for given parameter group: {error.args[0]}")
        raise GetAllParameterDBError


@db_session(optimistic=False)
def get_realtime_data(parameter_id=51, start_time=1655859600, end_time=1655874000):
    """

    Function used to return the real time data from the database for given parameter and time

    :param parameter_id: The parameter identifier
    :type parameter_id: int

    :param start_time: Start time for which the data needs to be queried in epoch format
    :type start_time: float

    :param end_time: End time for which the data needs to be queried in epoch format
    :type end_time: float

    :return: A List of list of machine parameter data and list of timestamp
    :rtype: list

    """

    try:

        # Converting the epoch format to datetime format (UTC- just like how it is stored in db)
        start_time_datetime = datetime.fromtimestamp(start_time, tz=pytz.timezone("UTC"))
        end_time_datetime = datetime.fromtimestamp(end_time, tz=pytz.timezone("UTC"))

        # Querying the real time data from the database for given parameter and time and sorting them using timestamp
        data = RealTimeParameter.select(lambda parameter: parameter.machine_parameter.id == parameter_id)
        data = data.filter(lambda parameter: parameter.time >= start_time_datetime)
        data = data.filter(lambda parameter: parameter.time <= end_time_datetime). \
                   sort_by(RealTimeParameter.time).for_update()[:]

        if data:
            return_data = [[record.time.timestamp() * 1000 for record in data], [record.value for record in data]]
            return return_data
    except Exception as error:
        LOGGER.exception(f"Exception while processing status of machine for given parameter group: {error.args[0]}")


@db_session(optimistic=False)
def get_recent_time_parameter(parameter_id=2711):
    """

    Function used to return the real time data from the database for given parameter and time

    :param parameter_id: The parameter identifier
    :type parameter_id: int

    :return: recent most timestamp of the given parameter
    :rtype: float

    """

    try:
        # Querying the real time data from the database for given parameter and time and sorting them using timestamp
        data = RealTimeParameter.select(lambda parameter: parameter.machine_parameter.id == parameter_id)
        data = data.sort_by(desc(RealTimeParameter.time)).for_update()[:1]

        if data:
            return_data = data[0].time.timestamp()
            return return_data
    except Exception as error:
        LOGGER.exception(f"Exception while processing status of machine for given parameter group: {error.args[0]}")


@db_session(optimistic=False)
def set_dynamic_parameter_reference_signals():
    """
    Function used to set the reference signal for dynamic parameters
    (that uses kruskal's method for anomaly detection)

    :return: A String containing the sql query
    :rtype: str
    """

    # query_template = get_all_recent_time_template()
    #
    # # Using a really complicated group by function along with timescale db inbuilt function
    # # To get the total number of warning and critical parameters
    # oldest_time_parameters = list(PONY_DATABASE.select(query_template))
    #
    # reference_signal_time = [(parameter[0], parameter[1], parameter[1] + timedelta(hours=1))
    #                          for parameter in oldest_time_parameters]
    #
    # for parameter in reference_signal_time:
    #     current_reference_signal = get_realtime_data(parameter[0], parameter[1].timestamp() + 19800,
    #                                                  parameter[2].timestamp() + 19800)
    #
    #     if current_reference_signal:
    #         current_reference_signal = current_reference_signal[1]
    #     else:
    #         continue
    #
    #     machine_parameter = MachineParameter[parameter[0]]
    #     machine_parameter.reference_signal = current_reference_signal
    #     commit()

    # Getting all the dynamic parameters
    dynamic_parameters = MachineParameter.select(lambda p: p.parameter_group.id == 17)

    for parameter in dynamic_parameters:
        real_time_data = RealTimeParameter.select(lambda p: p.machine_parameter == parameter)
        real_time_data = real_time_data.filter(lambda p: p.parameter_condition.id > 0)
        real_time_data = real_time_data.order_by(desc(RealTimeParameter.time))[:2]

        if len(real_time_data) == 2:

            reference_signal = RealTimeParameter.select(lambda p: p.time > real_time_data[1].time)
            reference_signal = reference_signal.filter(lambda p: p.time <= real_time_data[0].time)
            reference_signal = reference_signal.filter(lambda p: p.machine_parameter == parameter)
            reference_signal = reference_signal.order_by(RealTimeParameter.time)
        else:
            continue
        if reference_signal:
            set_reference_signal = []
            for signal in reference_signal:
                print(signal)
                set_reference_signal.append(signal.value)

            parameter.reference_signal = set_reference_signal
            commit()
    return


@db_session
def get_user(username: str):
    """
    GET USER
    ===========

    This function is used to return a Pydantic model of (active - disable = False) user if the user is in the database

    :param username: The user name who wants to log in

    :return: Return a pydantic class of user
    :rtype: UserInDB
    """

    user = UserPony.select(lambda current_user: current_user.username == username).first()

    if user:
        return UserInDB(**user.to_dict())


@db_session
def get_user_emails():
    """
    GET USER
    ===========

    This function is used to return all the email ids of available users

    :return: Return a list of email ids of users
    :rtype: list
    """

    email_ids = select(email.email_id for email in EmailUser)[:]

    print(list(email_ids))

    return email_ids


@db_session
def create_user(username: str, hashed_password: str, email: Optional[str] = None, full_name: Optional[str] = None):
    """
    CREATE USER
    ==============

    This function is used to create a new user

    :param username: The new user name
    :param email: The email of the new user
    :param full_name: The fullname of new user
    :param hashed_password: The hashed_password of new user

    :return: Return a pydantic class of user
    :rtype: User
    """

    user = UserPony.select(lambda current_user: current_user.username == username).first()

    if not user:
        user_orm = UserPony(username=username, email=email, full_name=full_name, hashed_password=hashed_password)
        # Not required to commit, but lets use if for testing purposes
        commit()
        return UserPydantic(**user_orm.to_dict())


@db_session
def get_spare_parts(machine_name: str):
    """
    GET SPARE PARTs
    =====================

    This function is used to get all the spare parts of machine

    :param machine_name: The machine name

    :return: Returns list of spare parts details
    :rtype: dict
    """

    machine = Machine.get(name=machine_name)

    if machine:
        spare_parts = list(machine.spare_parts)

        # Not required to commit, but committing for testing purpose.
        commit()

        # response_data = spare_parts.to_dict()
        response_data = []

        # Getting the machine part count object (Table)
        machine_part_count = MachinePartCount.get(machine=machine)

        # Getting the total part count of this machine
        total_part_count_of_machine = machine_part_count.current_part_count

        # For every spare part available in the machine, we do the following
        for part in spare_parts:

            # Converting the part pony object to dictionary
            part_details = part.to_dict()

            part_details["machine_id"] = part_details["machine"]

            # Getting the current part count for the spare part, by subtracting the reference
            # Part count/number from the total part count of machine.
            # The reference part count is equal to the total part count of machine when the
            # Spare part was created from the front end or equal to the total part count of machine when the
            # Spare part count was reset from the front end.
            current_spare_part_count = total_part_count_of_machine - part.reference_part_number

            part_details["count"] = current_spare_part_count
            response_data.append(part_details)

        response_data = {"total_count": total_part_count_of_machine, "spare_parts": response_data}

        return response_data


@db_session
def create_spare_part(machine_name: str, part_name: str, reference_part_number: int, warning_limit: int,
                      critical_limit: int):
    """
    CREATE SPARE PART
    =====================

    This function is used to create a new user

    :param machine_name: The machine name
    :param part_name: The part name
    :param reference_part_number: The reference part number
    :param warning_limit: The change limit for the part number
    :param critical_limit: The change limit for the part number

    :return: Return a pydantic class of user
    :rtype: PydanticSparePart
    """

    machine = Machine.select(lambda current_machine: current_machine.name == machine_name).first()

    if machine:
        spare_part_orm = SparePart(part_name=part_name, reference_part_number=reference_part_number,
                                   warning_limit=warning_limit, critical_limit=critical_limit, machine=machine)

        # Not required to commit, but lets use if for testing purposes
        commit()

        response_data = spare_part_orm.to_dict()
        response_data["machine_id"] = response_data["machine"]

        return PydanticSparePart(**response_data)


@db_session
def update_spare_part(machine_name: str, part_name: str, parameter_name: str, parameter_value: int):
    """
    CREATE SPARE PART
    =====================

    This function is used to create a new user

    :param machine_name: The machine name
    :param part_name: The part name
    :param parameter_name: The parameter name
    :param parameter_value: The reference part number

    :return: Return a pydantic class of spare part
    :rtype: PydanticSparePart
    """

    machine = Machine.select(lambda current_machine: current_machine.name == machine_name).first()

    spare_part = SparePart.select(lambda current_part: current_part.part_name == part_name)
    spare_part = spare_part.filter(lambda current_part: current_part.machine == machine).first()

    if spare_part:
        if parameter_name == "reference_part_number":
            spare_part.reference_part_number = parameter_value
        elif parameter_name == "warning_limit":
            spare_part.warning_limit = parameter_value
        else:
            spare_part.critical_limit = parameter_value

        # Not required to commit, but lets use if for testing purposes
        commit()

        response_data = spare_part.to_dict()
        response_data["machine_id"] = response_data["machine"]

        return PydanticSparePart(**response_data)


@db_session
def delete_spare_part(machine_name: str, part_name: str):
    """
    CREATE SPARE PART
    =====================

    This function is used to create a new user

    :param machine_name: The machine name
    :param part_name: The part name

    :return: Return a deleted message
    :rtype: dict
    """

    machine = Machine.select(lambda current_machine: current_machine.name == machine_name).first()

    spare_part = SparePart.select(lambda current_part: current_part.part_name == part_name)
    spare_part = spare_part.filter(lambda current_part: current_part.machine == machine).first()

    if spare_part:
        spare_part_name = spare_part.part_name

        spare_part.delete()

        # Not required to commit, but lets use if for testing purposes
        commit()

        return {"detail": "Successfully Deleted", "spare_part": spare_part_name}


@db_session
def get_alert_summary(condition_id: int = 3):
    """
    CREATE ALERT SUMMARY
    =======================

    This function is used to create a new user

    :param condition_id: The condition if for which the summary is to be created

    :return: List of alert summary
    :rtype: List
    """

    # If you dont use '*' in pony count,  (instead use something like p.time), it will result in
    # Using the keyword 'DISTINCT' within the count, that will result in less number
    # So if you simply want to get how many times a machine went to anomaly within given time, you can use
    # p.time in count (since every second more than 1 parameter might be in warning state, hence
    # You may have to use the keyword 'DISTINCT'.
    # parameters = select((p.machine_parameter.machine.name, p.machine_parameter.machine.location, pony_count("*"))
    #                     for p in RealTimeParameter if p.parameter_condition.id == 3)[:]

    # parameters = select((p.machine_parameter.machine.name, p.machine_parameter.machine.location, pony_count(p.time))
    #                     for p in RealTimeParameter if p.parameter_condition.id == 3)

    # This gives anomaly for each location, how many machines (not how many times all machine, so even if machine
    # had been in anomaly twice, it will be counted as one), and how many times (all) parameters were in anomaly
    # Order by -3 means order by the 3rd element of the resulting tuple in descending order
    parameters = select((p.machine_parameter.machine.location, pony_count(p.machine_parameter.machine.name),
                         pony_count("*")) for p in RealTimeParameter if p.parameter_condition.id == condition_id). \
        order_by(-3)

    return parameters[:]


@db_session(optimistic=False)
def update_parameter_limits(machine_name, parameter_group_id=5, axis_id=0,
                            set_type="warning_limit", limit=None, reference_signal=None,
                            append=False):
    """
    Retrieves the current machine's given parameter group and axis's full timeline information for given
    start and end time

    :param machine_name: The machine name whose data is required
    :type machine_name: str

    :param parameter_group_id: The parameter group identifier
    :type parameter_group_id: int

    :param axis_id: The parameter axis identifier
    :type axis_id: int

    :param set_type: The parameter axis identifier
    :type set_type: str

    :param limit: Start time for which the data needs to be queried in epoch format
    :type limit: float

    :param reference_signal: End time for which the data needs to be queried in epoch format
    :type reference_signal: Optional[list[float]]

    :param append: If the parameter type is dynamic, we're updating the reference signal, then we either append to
    the existing value or add a new value (list of values)
    :type append: bool

    :return: The current machine's full timeline information
    :rtype: dict

    """

    try:
        # Getting all the parameters for the given machine in the given parameter group
        machine_parameters = get_parameters(machine=machine_name, parameter_group_id=parameter_group_id)

        LOGGER.info(f"Requested parameters all:{machine_parameters}")

        if not machine_parameters:
            # If there was not data found, raise error
            raise GetMachineTimelineError("Invalid machine/ parameter identifier")

        if axis_id >= len(machine_parameters):
            # If the given axis_id is greater than than the total number of axes for the machine, raise error
            raise GetMachineTimelineError("Invalid axis identifier")

        # Get the actual parameter name
        requested_parameter_id = machine_parameters[axis_id]
        LOGGER.info(f"Requested parameter:{requested_parameter_id}")

        machine_parameter = MachineParameter[requested_parameter_id]

        if set_type == "warning_limit":
            if machine_parameter.parameter_type == "decreasing":
                if machine_parameter.critical_limit < limit:
                    machine_parameter.warning_limit = limit
                    response_data = {"set_type": "warning_limit",
                                     "value": limit}
                else:
                    raise Exception("Invalid limit, warning limit must be greater than the critical limit")
            else:
                if machine_parameter.critical_limit > limit:
                    machine_parameter.warning_limit = limit
                    response_data = {"set_type": "warning_limit",
                                     "value": limit}
                else:
                    raise Exception("Invalid limit, warning limit must be less than the critical limit")

        elif set_type == "critical_limit":
            if machine_parameter.parameter_type == "decreasing":
                if machine_parameter.warning_limit > limit:
                    machine_parameter.critical_limit = limit
                    response_data = {"set_type": "critical_limit",
                                     "value": limit}
                else:
                    raise Exception("Invalid limit, warning limit must be greater than the critical limit")
            else:
                if machine_parameter.warning_limit < limit:
                    machine_parameter.critical_limit = limit
                    response_data = {"set_type": "critical_limit",
                                     "value": limit}
                else:
                    raise Exception("Invalid limit, warning limit must be less than the critical limit")

        else:
            if append:
                if machine_parameter.reference_signal is not None:
                    machine_parameter.reference_signal.extend(reference_signal)
                else:
                    machine_parameter.reference_signal = reference_signal
            else:
                machine_parameter.reference_signal = reference_signal

            response_data = {"set_type": "dynamic_limit",
                             "value": reference_signal}

        commit()
        # response_data = {"detail": f"Successfully updated machine parameters limit for machine: {machine_name},"
        #                            f" parameter group id: {parameter_group_id}, axis id : {axis_id}"}

        return response_data

    except ObjectNotFound as error:
        LOGGER.error(f"The object not found in database: {error.args[0]}")
        raise GetMachineTimelineError
    except Exception as error:
        LOGGER.error(f"The issues with database: {error.args[0]}")
        raise GetMachineTimelineError(error.args[0])


def get_alarm_summary(start_time_datetime, end_time_datetime, production_line: str = r".*",
                      state="DISCONNECT"):
    """
    Function to get the total number of seconds between start and end time for given production_line/ machine and
    signal name

    :param start_time_datetime: The start time of the state.
    :type start_time_datetime: datetime

    :param end_time_datetime: The end time of the state
    :type end_time_datetime: datetime

    :param production_line: Name of production line or machine
    :type production_line: str

    :param state: The state of machine/production line
    :type state: str

    :return: Total time the machine/ production_line was in the given state in seconds
    :rtype: float
    """

    collection = get_mongo_collection()

    result_1 = collection.aggregate(get_exceed_group_template(signalname=state, production_line=production_line,
                                                              start_time_datetime=start_time_datetime,
                                                              end_time_datetime=end_time_datetime))

    result_2 = collection.aggregate(get_within_group_template(signalname=state, production_line=production_line,
                                                              start_time_datetime=start_time_datetime,
                                                              end_time_datetime=end_time_datetime))

    result_3 = collection.aggregate(get_between_head_group_template(signalname=state, production_line=production_line,
                                                                    start_time_datetime=start_time_datetime,
                                                                    end_time_datetime=end_time_datetime))

    result_4 = collection.aggregate(get_between_tail_group_template(signalname=state, production_line=production_line,
                                                                    start_time_datetime=start_time_datetime,
                                                                    end_time_datetime=end_time_datetime))

    results = [list(result_1), list(result_2), list(result_3), list(result_4)]

    total_seconds = 0

    for result in results:

        if result:
            total_seconds += float(result[0]['TOTAL_TIME_SECONDS'])

    # print("Total Time in seconds: ", total_seconds)

    return total_seconds


def get_total_time_state(start_time_datetime, end_time_datetime, production_line: str = r".*",
                         state="DISCONNECT"):
    """
    Function to get the total number of seconds between start and end time for given production_line/ machine and
    signal name

    :param start_time_datetime: The start time of the state.
    :type start_time_datetime: datetime

    :param end_time_datetime: The end time of the state
    :type end_time_datetime: datetime

    :param production_line: Name of production line or machine
    :type production_line: str

    :param state: The state of machine/production line
    :type state: str

    :return: Total time the machine/ production_line was in the given state in seconds
    :rtype: float
    """

    collection = get_mongo_collection()

    result_1 = collection.aggregate(get_exceed_group_template(signalname=state, production_line=production_line,
                                                              start_time_datetime=start_time_datetime,
                                                              end_time_datetime=end_time_datetime))

    result_2 = collection.aggregate(get_within_group_template(signalname=state, production_line=production_line,
                                                              start_time_datetime=start_time_datetime,
                                                              end_time_datetime=end_time_datetime))

    result_3 = collection.aggregate(get_between_head_group_template(signalname=state, production_line=production_line,
                                                                    start_time_datetime=start_time_datetime,
                                                                    end_time_datetime=end_time_datetime))

    result_4 = collection.aggregate(get_between_tail_group_template(signalname=state, production_line=production_line,
                                                                    start_time_datetime=start_time_datetime,
                                                                    end_time_datetime=end_time_datetime))

    results = [list(result_1), list(result_2), list(result_3), list(result_4)]

    total_seconds = 0

    for result in results:

        if result:
            total_seconds += float(result[0]['TOTAL_TIME_SECONDS'])

    # print("Total Time in seconds: ", total_seconds)

    return total_seconds


def get_total_time_day_state(start_time_datetime, end_time_datetime, production_line: str = r".*",
                             state="DISCONNECT"):
    """
    Function to get the total number of seconds in day  for given production_line/ machine and
    signal name

    :param start_time_datetime: The start time of the state.
    :type start_time_datetime: datetime

    :param end_time_datetime: The end time of the state
    :type end_time_datetime: datetime

    :param production_line: Name of production line or machine
    :type production_line: str

    :param state: The state of machine/production line
    :type state: str

    :return: Total time the machine/ production_line was in the given state in seconds
    :rtype: float
    """

    collection = get_mongo_collection()

    result_1 = collection.aggregate(get_exceed_group_day_template(signalname=state, production_line=production_line,
                                                                  start_time_datetime=start_time_datetime,
                                                                  end_time_datetime=end_time_datetime))

    result_2 = collection.aggregate(get_within_group_day_template(signalname=state, production_line=production_line,
                                                                  start_time_datetime=start_time_datetime,
                                                                  end_time_datetime=end_time_datetime))

    result_3 = collection.aggregate(get_between_head_group_day_template(signalname=state,
                                                                        production_line=production_line,
                                                                        start_time_datetime=start_time_datetime,
                                                                        end_time_datetime=end_time_datetime))

    result_4 = collection.aggregate(get_between_tail_group_day_template(signalname=state,
                                                                        production_line=production_line,
                                                                        start_time_datetime=start_time_datetime,
                                                                        end_time_datetime=end_time_datetime))

    results = [list(result_1), list(result_2), list(result_3), list(result_4)]

    total_seconds = 0

    for result in results:

        if result:
            total_seconds += float(result[0]['TOTAL_TIME_SECONDS'])

    # print("Total Time in seconds: ", total_seconds)

    return total_seconds


def get_alarm_summary_data(start_time, end_time, machine_name):
    """
    Function to get all the data required for full alarm summary of a machine between given start and end time

    :param start_time: The start time of the state.
    :type start_time: float

    :param end_time: The end time of the state
    :type end_time: float

    :param machine_name: Name of machine
    :type machine_name: str

    :return: Alarm summary data for machine
    :rtype: dict
    """

    start_time_datetime = datetime.fromtimestamp(start_time, tz=pytz.timezone("UTC"))
    end_time_datetime = datetime.fromtimestamp(end_time, tz=pytz.timezone("UTC"))

    collection = get_mongo_collection(collection="Alarm_History")
    # collection = get_mongo_collection(collection="Alarm History")

    result_1 = collection.aggregate(get_count_group_template(start_time_datetime=start_time_datetime,
                                                             end_time_datetime=end_time_datetime,
                                                             machine_name=machine_name))

    result_2 = collection.aggregate(get_timespan_group_template(start_time_datetime=start_time_datetime,
                                                                end_time_datetime=end_time_datetime,
                                                                machine_name=machine_name))

    result_3 = collection.aggregate(get_timeline_group_template(start_time_datetime=start_time_datetime,
                                                                end_time_datetime=end_time_datetime,
                                                                machine_name=machine_name))

    results = {"data": {"count_data": list(result_1), "timespan_data": list(result_2),
                        "timeline_data": list(result_3)}}

    return results


def get_all_states_summary(production_line, start_time_datetime, end_time_datetime):
    """
    Function to get all the states summary of states for a given production line or machine

    :param production_line: The machine name of production_line
    :type production_line: str

    :param start_time_datetime: The start time for the query
    :type start_time_datetime: datetime

    :param end_time_datetime: The end time for the query
    :type end_time_datetime: datetime

    :return: Dictionary of total time for each state of machines/production_line
    :rtype: dict
    """
    states = {"OPERATE": 0, "MANUAL": 0, "STOP": 0, "ALARM": 0,
              "EMERGENCY": 0, "SUSPEND": 0, "DISCONNECT": 0}

    for state in states.keys():
        states[state] = get_total_time_state(state=state, production_line=production_line,
                                             start_time_datetime=start_time_datetime,
                                             end_time_datetime=end_time_datetime)
    # pprint.pprint(states)

    return states


def get_all_states_day_summary(production_line, start_time_datetime, end_time_datetime):
    """
    Function to get all the states summary of states for a given production line or machine

    :param production_line: The machine name of production_line
    :type production_line: str

    :param start_time_datetime: The start time for the query
    :type start_time_datetime: datetime

    :param end_time_datetime: The end time for the query
    :type end_time_datetime: datetime

    :return: Dictionary of total time for each state of machines/production_line
    :rtype: dict
    """
    states = {"OPERATE": 0, "MANUAL": 0, "STOP": 0, "ALARM": 0,
              "EMERGENCY": 0, "SUSPEND": 0, "DISCONNECT": 0}

    for state in states.keys():
        states[state] = get_total_time_day_state(state=state, production_line=production_line,
                                                 start_time_datetime=start_time_datetime,
                                                 end_time_datetime=end_time_datetime)
    # pprint.pprint(states)

    return states


def get_full_day_summary(production_line=r'.*', day: int = 1655596800):
    """
    Function to get the full day summary of a production line/ machine for all states

    :param production_line: The machine name or production line to get the full day summary
    :type production_line: str

    :param day: The epoch timestamp of the date at exactly 12:00 AM
    :type day: int

    :return: Full day's statics for all state of machine
    :rtype: dict
    """

    day_start = int(day)
    day_end = 86400 + day

    time_slots = [(slot, slot + 3600) for slot in range(day_start, day_end - 3600 + 1, 3600)]

    full_day_stats = []

    current_hour = 0

    for current_time in time_slots:
        current_time_stats = get_all_states_summary(production_line=production_line,
                                                    start_time_datetime=datetime.fromtimestamp(current_time[0],
                                                                                               tz=pytz.timezone("UTC")),
                                                    end_time_datetime=datetime.fromtimestamp(current_time[1],
                                                                                             tz=pytz.timezone("UTC")))
        full_day_stats.append({"current_hour_day": current_hour, "data": current_time_stats})
        current_hour += 1
    full_day = {"OPERATE": 0, "MANUAL": 0, "STOP": 0, "ALARM": 0,
                "EMERGENCY": 0, "SUSPEND": 0, "DISCONNECT": 0}

    for hour in full_day_stats:
        for state in full_day.keys():
            full_day[state] += hour["data"][state]

    full_day_stats.append({"current_hour_day": current_hour, "data": full_day})

    pprint.pprint(full_day_stats)

    return full_day_stats


def get_full_month_week_summary(production_line=r'.*', day: int = 1654043400, week=False):
    """
    Function to get the full month summary of a production line/ machine for all states

    :param production_line: The machine name or production line to get the full day summary
    :type production_line: str

    :param day: The epoch timestamp of the first day of the month at exactly 12:00 AM
    :type day: int

    :param week:
    :type week:

    :return: Full day's statics for all state of machine
    :rtype: dict
    """

    # program_start_time = time.time()

    day_start = int(day)

    day_object = datetime.fromtimestamp(day_start, tz=pytz.timezone("UTC"))

    number_of_days = calendar.monthrange(day_object.year, day_object.month)[1]

    if week:
        day_end = 604800 + day
    else:
        day_end = (number_of_days * 86400) + day

    day_slots = [(slot, slot + 86400) for slot in range(day_start, day_end - 86400 + 1, 86400)]

    full_month_week_stats = []

    current_day = 0

    for current_time in day_slots:
        current_time_stats = get_all_states_day_summary(production_line=production_line,
                                                        start_time_datetime=datetime.fromtimestamp(current_time[0],
                                                                                                   tz=pytz.timezone(
                                                                                                       "UTC")),
                                                        end_time_datetime=datetime.fromtimestamp(current_time[1],
                                                                                                 tz=pytz.timezone(
                                                                                                     "UTC")))
        full_month_week_stats.append({"current_hour_day": current_day, "data": current_time_stats})
        current_day += 1

    full_month_week = {"OPERATE": 0, "MANUAL": 0, "STOP": 0, "ALARM": 0,
                       "EMERGENCY": 0, "SUSPEND": 0, "DISCONNECT": 0}

    for day in full_month_week_stats:
        for state in full_month_week.keys():
            full_month_week[state] += day["data"][state]

    full_month_week_stats.append({"current_hour_day": current_day, "data": full_month_week})

    pprint.pprint(full_month_week_stats)

    # print("Total Time For Program: " + str(time.time() - program_start_time))

    return full_month_week_stats


@db_session
def test_function(machine="T_B_OP160", parameter_group_id=1):
    """

    Function to get all parameters for a given machine in a given parameter group (identifier)

    :param machine: The machine for which the parameters are required
    :type machine: str

    :param parameter_group_id: The parameter group identifier
    :type parameter_group_id: int

    :return: List of sorted (by name) parameter (identifier) for the given machine and parameter group
    :rtype: list

    """

    try:

        current_value_base_query = RealTimeParameter. \
            select(lambda parameter: parameter.machine_parameter.id == 3211)

        current_value = list(current_value_base_query.order_by(desc(RealTimeParameter.time)).for_update()[:1])
        print(current_value[0])
        non_ok_data = select(c for c in current_value if c.parameter_condition.id > 1)
        print(list(non_ok_data))
    except Exception as error:
        LOGGER.exception(f"Exception while processing status of machine for given parameter group: {error.args[0]}")
        raise GetAllParameterDBError


def main():
    # get_current_machine_data()

    # get_parameters()

    # get_realtime_data()

    # get_alert_summary()

    # get_full_month_week_summary()
    # get_full_month_week_summary(week=True)

    # get_full_day_summary()

    # data = get_alarm_summary_data(start_time=1654682400, end_time=1655118000, machine_name="T_H_OP50")

    # pprint.pprint(data, indent=1)

    # get_user_emails()

    # get_all_parameter_group_status()

    # test_function()

    # get_recent_time_parameter()

    set_dynamic_parameter_reference_signals()


if __name__ == '__main__':
    # initialize_pony()
    main()
