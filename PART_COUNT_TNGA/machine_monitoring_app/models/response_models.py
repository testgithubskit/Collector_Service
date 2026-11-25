#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Response Model Classes
================================

Module that contains pydantic classes for the api endpoint response models in the application

This script requires the following modules be installed in the python environment
    * logging - To perform logging operations.
    * pydantic - To perform data validation and settings management using python type annotations.
"""

# Standard library imports
from enum import IntEnum
from typing import Union, Optional
# Related third party imports
from pydantic import BaseModel

# Local application/library specific imports
# None

__author__ = "smt18m005@iiitdm.ac.in"


class StateEnum(IntEnum):
    """

    This class represents the enum type that will be used to represent the three machine/ parameter states

    """
    OK = 1
    WARNING = 2
    CRITICAL = 3


class ParameterData(BaseModel):
    """

    This is used as part of the response model, that denotes the individual parameters (will be used by MachineData)

    """

    # Represents the parameter name (as integer)
    name: int

    # Represents the parameter name (as string)
    actual_name: str

    # Represents the recent update timestamp for the parameter
    last_update_time: float

    # Represents the value of the parameter
    value: float

    # Represents the status of the parameter
    status: StateEnum


class MachineData(BaseModel):
    """

    This is used as response model for current status of the machine

    """

    # Represents the machine name
    name: str

    # Represents the machine state, either ok, warning or critical
    status: StateEnum

    # Represents the requested parameters
    axes: list[ParameterData]


class CurrentData(BaseModel):
    """

    This is used as response model for current status of the machine

    """

    # Represents the parameter name (as integer)
    param: int

    # Represents the actual parameter name in the database
    param_actual_name: str

    # All machines data
    machines: list[MachineData]

    # State of parameter group
    params_group_status: list[StateEnum]


class FullTimelineData(BaseModel):
    """

    This is used as response model for sending full timeline data of a given machine, parameter group
    and axis

    """

    # Represents the parameter name (as integer)
    param: int

    # Represents the axis identifier (as integer)
    axis: int

    # Represents the actual machine name in the database
    machine: str

    # Start time of query
    start_time: float

    # End time of query
    stop_time: float

    # Real time data of the parameter
    data: list[float]

    # Corresponding parameters
    timestamps: list[float]

    # critical limit values
    critical_limit: Optional[float]

    # warning limit values
    warning_limit: Optional[float]


class StatusSummaryData(BaseModel):
    """

    This is used as response model for sending full timeline data of a given machine, parameter group
    and axis

    """

    # Represents the total time in seconds the machine/ all machines in production line was
    # ALARM state
    ALARM: int

    # Represents the total time in seconds the machine/ all machines in production line was
    # DISCONNECT state
    DISCONNECT: int

    # Represents the total time in seconds the machine/ all machines in production line was
    # EMERGENCY state
    EMERGENCY: int

    # Represents the total time in seconds the machine/ all machines in production line was
    # MANUAL state
    MANUAL: int

    # Represents the total time in seconds the machine/ all machines in production line was
    # OPERATE state
    OPERATE: int

    # Represents the total time in seconds the machine/ all machines in production line was
    # STOP state
    STOP: int

    # Represents the total time in seconds the machine/ all machines in production line was
    # SUSPEND state
    SUSPEND: int


class StatusSummary(BaseModel):
    """

    This is used as response model for sending full timeline data of a given machine, parameter group
    and axis

    """

    # Represents the hour/day (time slot) for the summary data
    current_hour_day: int

    # Represents the actual data
    data: StatusSummaryData


class StatusSummaryResponseData(BaseModel):
    """

    This is used as response model for sending full timeline data of a given machine, parameter group
    and axis

    """

    # Represents the hour (time slot) for the summary data
    requested_time: int

    requested_factory_object: str

    requested_day_range: str

    # Represents the actual data
    requested_data: list[StatusSummary]


class SparePart(BaseModel):
    """
    Represents the spare part model used as response model for sending back the created data to client
    """

    # Represent the row id
    id: int

    # Represents the spare part name
    part_name: str

    # Represents the reference part number
    reference_part_number: int

    # Represents the warning set limit
    warning_limit: int

    # Represents the critical set limit
    critical_limit: int

    # Represents the machine identifier
    machine_id: int

    # Represents the default count of the spare part
    count: int = 0


class GetSparePartResponse(BaseModel):
    """
    Represents the spare part model used as response model for sending back the created data to client
    """

    # Represent the total part count from the machine
    total_count: int

    # Represents the individual spare part details
    spare_parts: list[SparePart]


class AlarmCountData(BaseModel):
    """
    Represents the alarm summary response model used as response model for sending back the alarm
    summary data to client
    """

    # Represent the message / alarm name
    message: str

    # Represents the alarm count
    total_count: int


class AlarmTimeData(BaseModel):
    """
    Represents the alarm timespan summary response model used as response model for sending back the alarm
    summary data to client
    """

    # Represent the message / alarm name
    message: str

    # Represents the alarm timespan in seconds
    total_time: float


class AlarmTimelineData(BaseModel):
    """
    Represents the alarm timespan summary response model used as response model for sending back the alarm
    summary data to client
    """

    # Represent the start time of the alarm in epoch seconds
    enddate_epoch_time: float

    # Represent the end  time of the alarm in epoch seconds
    update_epoch_time: float

    message: str


class AlarmModel(BaseModel):
    """
    Represents the alarm summary response model used as response model for sending back the alarm
    summary data to client
    """

    # Represent the row id
    count_data: list[AlarmCountData]

    timespan_data: list[AlarmTimeData]

    timeline_data: list[AlarmTimelineData]


class AlarmSummaryResponseModel(BaseModel):
    """
    Represents the alarm summary response model used as response model for sending back the alarm
    summary data to client
    """

    # Represent the row id
    data: AlarmModel


class SpareDeleteResponseModel(BaseModel):
    """
    Represents the alarm summary response model used as response model for sending back the alarm
    summary data to client
    """

    # Represent the row id
    detail: str

    # Name of the spare part that was deleted
    spare_part: str


class UpdateParameterLimitResponseModel(BaseModel):
    """
    Represents the alarm summary response model used as response model for sending back the alarm
    summary data to client
    """

    # Represents the parameter set type
    set_type: str

    # Represents the parameter set value
    value: Union[float, list[float]]
