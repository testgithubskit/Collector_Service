# -*- coding: utf-8 -*-
"""
CORE DATA ROUTES MODULE TEST
=====================================

This Module consists of api routes for get access to core data

This script requires that the following packages be installed within the Python
environment you are running this script in.

    Standard Library
    =================

    * logging - To perform logging operations.

    Related 3rd Party Library
    =============================

    * fastapi - To perform web application (backend) related functions.

This script contains the following function


    * read_all_current_values - This is an api endpoint used to query the latest data from the database.
"""

# Standard Imports
import logging
import time
from typing import Union, Optional

# Related third party imports
from fastapi import APIRouter, Depends, HTTPException, status
import pandas as pd
import psycopg2

# Local application/library specific imports
from machine_monitoring_app.models.response_models import CurrentData, FullTimelineData, StatusSummaryResponseData, \
    SparePart, AlarmSummaryResponseModel, SpareDeleteResponseModel, GetSparePartResponse, \
    UpdateParameterLimitResponseModel

from machine_monitoring_app.database.crud_operations import get_current_machine_data, get_machine_timeline, \
    create_spare_part, update_spare_part, get_alarm_summary_data, delete_spare_part, update_parameter_limits

from machine_monitoring_app.database import get_timescaledb_url
from machine_monitoring_app.exception_handling.custom_exceptions import NoParameterGroupError, GetParamGroupDBError, \
    GetAllParameterDBError, GetMachineTimelineError

from machine_monitoring_app.routers.router_dependencies import get_current_active_user
from machine_monitoring_app.database.crud_operations import get_full_day_summary, get_full_month_week_summary, \
    get_spare_parts

from machine_monitoring_app.models.base_data_models import User

LOGGER = logging.getLogger(__name__)

# Depends(get_current_active_user)
ROUTER = APIRouter(
    prefix="/api/v1",
    tags=["Core Data Routes"],
    dependencies=[Depends(get_current_active_user)],
    responses={404: {"description": "Not found"}})


@ROUTER.get("/machine-state/{parameterGroupId}", response_model=CurrentData)
async def read_all_current_values(parameterGroupId: int):
    """

    GET CURRENT PARAMETERS DATA
    ===============================

    This api is used to query the status of the machines for given parameter group

    """

    start_time = time.time()
    try:
        response_data = get_current_machine_data(parameterGroupId)
        LOGGER.info(time.time() - start_time)
    except NoParameterGroupError as error:
        raise HTTPException(status_code=404, detail=f"Parameter group id '{parameterGroupId}' is not found")
    except GetParamGroupDBError as error:
        raise HTTPException(status_code=500, detail="Internal Server Error")
    except GetAllParameterDBError as error:
        raise HTTPException(status_code=500, detail="Internal Server Error")

    return response_data


@ROUTER.get("/{machineName}/{parameterGroupId}/{axisId}", response_model=FullTimelineData)
async def read_timeline_machine_param(machineName: str, parameterGroupId: int, axisId: int, startTime: float,
                                      endTime: float):
    """

    GET MACHINE TIMELINE DATA
    ===============================

    This api is used to query the given machine's parameter for full timeline of data

    """
    print("INSIDE FUNCTION")
    process_start_time = time.time()
    if startTime > endTime:
        raise HTTPException(status_code=400, detail="Start Time cannot be greater than End Time")
    try:
        response_data = get_machine_timeline(machineName, parameterGroupId, axisId, startTime, endTime)

        if response_data:
            LOGGER.info(time.time() - process_start_time)
            return response_data

        # If there is no response, raise an exception
        raise HTTPException(status_code=404, detail="No data available for given machine, parameter group, "
                                                    "axis and timestamp")
    except GetMachineTimelineError as error:
        raise HTTPException(status_code=404, detail=f"Issue with database: {error.args[0]}")


@ROUTER.get("/factory-state-summary", response_model=StatusSummaryResponseData)
def read_factory_state_summary(startTime: int, factoryObject: str = "all", dayRange: str = "month"):
    """

    GET MACHINE TIMELINE DATA
    ===============================

    This api is used to query the given machine's parameter for full timeline of data

    """

    process_start_time = time.time()

    if dayRange == "day":
        try:
            if factoryObject == "all":
                response_data = get_full_day_summary(day=startTime)
            else:
                response_data = get_full_day_summary(production_line=factoryObject, day=startTime)

            if response_data:
                LOGGER.info(time.time() - process_start_time)
                response_data = {"requested_time": startTime, "requested_factory_object": factoryObject,
                                 "requested_data": response_data, "requested_day_range": dayRange}
                return response_data

            # If there is no response, raise an exception
            raise HTTPException(status_code=404, detail="No data available for given machine, production_line")
        except Exception as error:
            raise HTTPException(status_code=404, detail=f"Issue with database: {error.args[0]}")
    elif dayRange == "month":
        try:
            if factoryObject == "all":
                response_data = get_full_month_week_summary(day=startTime)
            else:
                response_data = get_full_month_week_summary(production_line=factoryObject, day=startTime)

            if response_data:
                LOGGER.info(time.time() - process_start_time)
                response_data = {"requested_time": startTime, "requested_factory_object": factoryObject,
                                 "requested_data": response_data, "requested_day_range": dayRange}
                return response_data

            # If there is no response, raise an exception
            raise HTTPException(status_code=404, detail="No data available for given machine, production_line")
        except Exception as error:
            raise HTTPException(status_code=404, detail=f"Issue with database: {error.args[0]}")
    else:
        try:
            if factoryObject == "all":
                response_data = get_full_month_week_summary(day=startTime, week=True)
            else:
                response_data = get_full_month_week_summary(production_line=factoryObject, day=startTime, week=True)

            if response_data:
                LOGGER.info(time.time() - process_start_time)
                response_data = {"requested_time": startTime, "requested_factory_object": factoryObject,
                                 "requested_data": response_data, "requested_day_range": dayRange}
                return response_data

            # If there is no response, raise an exception
            raise HTTPException(status_code=404, detail="No data available for given machine, production_line")
        except Exception as error:
            raise HTTPException(status_code=404, detail=f"Issue with database: {error.args[0]}")


@ROUTER.get("/{machineName}/alarms", response_model=AlarmSummaryResponseModel)
def read_alarm_summary(machineName: str, startTime: float, endTime: float):
    """
    GET MACHINE ALARM DATA
    ===============================

    This api is used to query the given machine's parameter for full timeline of data
    """

    process_start_time = time.time()
    if startTime > endTime:
        raise HTTPException(status_code=400, detail="Start Time cannot be greater than End Time")
    try:

        response_data = get_alarm_summary_data(start_time=startTime, end_time=endTime,
                                               machine_name=machineName)

        if response_data:
            LOGGER.info(time.time() - process_start_time)
            return response_data

        # If there is no response, raise an exception
        raise HTTPException(status_code=404, detail="No data available for given machine, parameter group, "
                                                    "axis and timestamp")
    except GetMachineTimelineError as error:
        raise HTTPException(status_code=404, detail=f"Issue with database: {error.args[0]}")


@ROUTER.get("/{machineName}/spareParts", response_model=GetSparePartResponse)
def get_spare_parts_method(machineName):
    """
    GET MACHINE SPARE PARTs
    ===============================

    This api is used to get all the spare parts of a machine
    """

    process_start_time = time.time()

    spare_part = get_spare_parts(machine_name=machineName)

    if spare_part:
        return spare_part
    LOGGER.info(f"Total Time Taken: {time.time() - process_start_time}")

    # If there is no response, raise an exception
    raise HTTPException(status_code=404, detail="Given Machine Not Available")


@ROUTER.post("/{machineName}/{sparePart}", response_model=SparePart)
def create_spare_part_method(machineName, sparePart: str, referencePartNumber: int, warningLimit: int,
                             criticalLimit: int,
                             current_user: User = Depends(get_current_active_user)):
    """
    POST MACHINE SPARE PART
    ===============================

    This api is used to add new spare part to the machine
    """

    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authorized to create spare part, Only admin can create",
            headers={"WWW-Authenticate": "Bearer"},
        )

    process_start_time = time.time()

    spare_part = create_spare_part(part_name=sparePart, reference_part_number=referencePartNumber,
                                   warning_limit=warningLimit, critical_limit=criticalLimit,
                                   machine_name=machineName)

    if spare_part:
        return spare_part

    LOGGER.info(f"Total Time Taken: {time.time() - process_start_time}")

    # If there is no response, raise an exception
    raise HTTPException(status_code=404, detail="Given Machine Not Available")


@ROUTER.put("/{machineName}/{sparePart}", response_model=SparePart)
def update_spare_part_method(machineName: str, sparePart: str, parameterName: str, parameterValue: int,
                             current_user: User = Depends(get_current_active_user)):
    """
    UPDATE MACHINE SPARE PART
    ===============================

    This api is used to add new spare part to the machine
    """

    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authorized to update, Only admin can update",
            headers={"WWW-Authenticate": "Bearer"},
        )

    process_start_time = time.time()

    spare_part = update_spare_part(part_name=sparePart, parameter_value=parameterValue,
                                   machine_name=machineName, parameter_name=parameterName)

    if spare_part:
        return spare_part

    LOGGER.info(f"Total Time Taken: {time.time() - process_start_time}")

    # If there is no response, raise an exception
    raise HTTPException(status_code=404, detail="Given Spare Part Not Found")


@ROUTER.put("/parameters_limit/{machineName}/{parameterGroupId}/{axisId}",
            response_model=UpdateParameterLimitResponseModel)
def update_set_limit_method(machineName: str, parameterGroupId: int, axisId: int, setType: str,
                            limit: Optional[float] = None, append: Optional[bool] = None,
                            referenceSignal: Optional[list[float]] = None,
                            current_user: User = Depends(get_current_active_user)):
    """
    UPDATE MACHINE PARAMETER  SET LIMITS
    =========================================

    This api is used to update machine parameters set limit or reference signal
    """

    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authorized to update, Only admin can update",
            headers={"WWW-Authenticate": "Bearer"},
        )

    process_start_time = time.time()

    try:

        update_response = update_parameter_limits(machine_name=machineName, parameter_group_id=parameterGroupId,
                                                  axis_id=axisId, set_type=setType, limit=limit,
                                                  reference_signal=referenceSignal, append=append)

        if update_response:
            return update_response

        LOGGER.info(f"Total Time Taken: {time.time() - process_start_time}")

        # If there is no response, raise an exception
        raise HTTPException(status_code=404, detail="Given machine or parameter group or axis not found")
    except Exception as error:
        LOGGER.error(f"Error Occurred : {error.args[0]}")
        raise HTTPException(status_code=500, detail=f"Internal Error {error.args[0]}")


@ROUTER.delete("/{machineName}/{sparePart}", response_model=SpareDeleteResponseModel)
def delete_spare_part_method(machineName: str, sparePart: str, current_user: User = Depends(get_current_active_user)):
    """
    POST MACHINE SPARE PART
    ===============================

    This api is used to add new spare part to the machine
    """

    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authorized to delete, Only admin can delete spare parts",
            headers={"WWW-Authenticate": "Bearer"},
        )

    process_start_time = time.time()

    response = delete_spare_part(part_name=sparePart, machine_name=machineName)

    if response:
        return response

    LOGGER.info(f"Total Time Taken: {time.time() - process_start_time}")

    # If there is no response, raise an exception
    raise HTTPException(status_code=404, detail="Given Spare Part / Machine Not Found")


@ROUTER.get("/laser-cladding-machine-1")
def read_laser_clad(part_number: str):
    time_1 = time.time()
    with psycopg2.connect(get_timescaledb_url()) as conn:
        cursor = conn.cursor()
        sql_statement_part_timing = f"SELECT start_time, end_time FROM tiei_sample_4.machine_production_timeline " \
                                    f"WHERE part_number = '{part_number}'; "
        # _3611242204282543
        cursor.execute(sql_statement_part_timing)
        part_timing = cursor.fetchone()

        if not part_timing:
            raise HTTPException(status_code=404, detail="Part Number Not Found")
        # print(part_timing[0], part_timing[1])
        sql_for_real_time_data = "SELECT time, machine_parameters_id, value FROM " \
                                 f"tiei_sample_4.real_time_machine_parameters WHERE time " \
                                 f"BETWEEN '{str(part_timing[0])}'AND '{str(part_timing[1])}' " \
                                 f"AND machine_parameters_id IN (23, 24, 25, 26, 27, 28, 29)" \
                                 f"ORDER BY time;"
        # 2022-04-29 08:36:50+00, 2022-04-29 08:41:20.2+00
        cursor.execute(sql_for_real_time_data)
        real_time_data = cursor.fetchall()

        if not real_time_data:
            raise HTTPException(status_code=404, detail="No Data for Given Part")

    real_time_data = pd.DataFrame(real_time_data, columns=["time", "machine_parameters_id", "value"])
    real_time_data = real_time_data.pivot_table(index=["time"], columns="machine_parameters_id",
                                                values="value").reset_index()
    real_time_data = real_time_data.iloc[:, [0, 2, 1, 3, 4, 5, 6, 7]]
    LOGGER.info(real_time_data.iloc[:, 1:].head())
    data = {"name": part_number, "time": real_time_data.iloc[0, 0],
            "data": real_time_data.iloc[:, 1:].values.tolist()}
    time_2 = time.time()
    LOGGER.info(f"TOTAL TIME: {(time_2 - time_1) * 1000} ms")
    return data


@ROUTER.get("/laser-cladding-machine-1/real-time")
def read_laser_clad_time(part_number: Union[str, None] = None, start_time: Union[str, None] = None,
                         end_time: Union[str, None] = None):
    time_1 = time.time()

    if part_number:

        with psycopg2.connect(get_timescaledb_url()) as conn:
            cursor = conn.cursor()
            sql_statement_part_timing = f"SELECT start_time, end_time FROM tiei_sample_4.machine_production_timeline " \
                                        f"WHERE part_number = '{part_number}'; "
            # _3611242204282543
            cursor.execute(sql_statement_part_timing)
            part_timing = cursor.fetchone()

            if not part_timing:
                raise HTTPException(status_code=404, detail="Part Number Not Found")

            # print(part_timing[0], part_timing[1])
            sql_for_real_time_data = "SELECT extract(epoch from time) AS time, machine_parameters_id, value FROM " \
                                     f"tiei_sample_4.real_time_machine_parameters WHERE time " \
                                     f"BETWEEN '{str(part_timing[0])}'AND '{str(part_timing[1])}' " \
                                     f"AND machine_parameters_id IN (23, 24, 25, 26, 27, 28, 29)" \
                                     f"ORDER BY time;"
            # 2022-04-29 08:36:50+00, 2022-04-29 08:41:20.2+00
            cursor.execute(sql_for_real_time_data)
            real_time_data = cursor.fetchall()

            if not real_time_data:
                raise HTTPException(status_code=404, detail="No Data for Given Part")

    else:
        if (not start_time) or (not end_time):
            raise HTTPException(status_code=400, detail="Either part number or start and end time is required")
        LOGGER.info("Start Time: " + start_time)
        LOGGER.info("End Time: " + end_time)
        with psycopg2.connect(get_timescaledb_url()) as conn:
            cursor = conn.cursor()

            sql_for_real_time_data = "SELECT extract(epoch from time) AS time, machine_parameters_id, value FROM " \
                                     f"tiei_sample_4.real_time_machine_parameters WHERE time " \
                                     f"BETWEEN '{start_time}'AND '{end_time}' " \
                                     f"AND machine_parameters_id IN (23, 24, 25, 26, 27, 28, 29)" \
                                     f"ORDER BY time;"
            # 2022-04-29 08:36:50+00, 2022-04-29 08:41:20.2+00
            cursor.execute(sql_for_real_time_data)
            real_time_data = cursor.fetchall()

            if not real_time_data:
                raise HTTPException(status_code=404, detail="No Data for Given Time Range")

    real_time_data = pd.DataFrame(real_time_data, columns=["time", "machine_parameters_id", "value"])
    real_time_data = real_time_data.pivot_table(index=["time"], columns="machine_parameters_id",
                                                values="value").reset_index()
    real_time_data = real_time_data.iloc[:, [0, 2, 1, 3, 4, 5, 6, 7]]
    LOGGER.info(real_time_data.head())

    if part_number:

        data = {"name": part_number, "start_time": real_time_data.iloc[0, 0],
                "end_time": real_time_data.iloc[-1, 0],
                "data": real_time_data.values.tolist()}
    else:

        data = {"start_time": real_time_data.iloc[0, 0],
                "end_time": real_time_data.iloc[-1, 0],
                "data": real_time_data.values.tolist()}

    time_2 = time.time()
    LOGGER.info(f"TOTAL TIME: {(time_2 - time_1) * 1000} ms")
    return data


@ROUTER.get("/laser-cladding-machine-1/similar-part")
def read_laser_clad_similar_part(part_number: str):
    time_1 = time.time()
    with psycopg2.connect(get_timescaledb_url()) as conn:
        cursor = conn.cursor()
        sql_statement_part_timing = "SELECT part_number	FROM tiei_sample_4.machine_production_timeline WHERE " \
                                    f"part_number LIKE '%{part_number}%';"

        # _3611242204282543
        cursor.execute(sql_statement_part_timing)
        parts = cursor.fetchall()
        parts = [p[0] for p in parts]
        if not parts:
            raise HTTPException(status_code=404, detail="Part Number Not Found")

    data = {"part_ending": part_number,
            "data": parts}
    time_2 = time.time()
    LOGGER.info(f"TOTAL TIME: {(time_2 - time_1) * 1000} ms")
    return data
