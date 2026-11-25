#!/usr/bin/python
# -*- coding: utf-8 -*-
"""

================================

Module for  application to

This script requires the following modules be installed in the python environment
    * logging - to perform logging operations

This script contains the following function
    * main - main function to call appropriate functions to find the contours in the video
"""

# Standard library imports
import logging
# Related third party imports


# Local application/library specific imports


__author__ = "smt18m005@iiitdm.ac.in"

LOGGER = logging.getLogger(__name__)


class NoDataFromMongoDB(Exception):
    pass


class MongoDbConnectionFailure(Exception):
    pass


class MtLinkiGetNewDataParametersGroupClassFailure(Exception):
    """

    This exception is used when the ParametersGroupBase class's method get_new_data is not able to get new data
    from the MtLinki, due to connectivity issues.

    """
    pass


class TimescaleDbConnectionFailure(Exception):
    pass


class MachineIdQueryFailure(Exception):
    pass


class ParameterIdQueryFailure(Exception):
    pass


class GetReferenceSignalFailure(Exception):
    pass


class GetDynamicConfigFailure(Exception):
    """

    This exception is used when the get_dynamic_config from the db_utils module is not able to get the dynamic
    parameters configuration details

    """
    pass


class SetDynamicConfigFailure(Exception):
    """

    This exception is used when the update_latest_time from the db_utils module is not able to update the latest
    update time for a given parameter group

    """
    pass


class AddConditionColumnParametersGroupClassFailure(Exception):
    """

    This exception is used when the ParametersGroupBase class's method add_condition_columns is not able to add new
    new column "condition" to the recent data

    """
    pass


class InsertTimescaleParametersGroupClassFailure(Exception):
    """

    This exception is used when the ParametersGroupBase class's method insert_to_timescaledb is not able to insert new
    data into timescaledb due to database connectivity or operational error

    """
    pass


class CheckAnomalyParametersGroupClassFailure(Exception):
    """

    This exception is used when the ParametersGroupBase class's method check_for_new_anomaly gets an error

    """
    pass


class SendAnomalyParametersGroupClassFailure(Exception):
    """

    This exception is used when the ParametersGroupBase class's method check_for_new_anomaly gets an error

    """
    pass


class LoadConfigFailure(Exception):
    """

    This exception is used when there is an exception while loading config file such as log configuration

    """
    pass


class LoadParamCollectorClassFailure(Exception):
    """

    This exception is used when the CollectorClass class's method load_parameters gets an error while loading
    the parameters

    """
    pass


class WorkflowCollectorClassFailure(Exception):
    """

    This exception is used when the CollectorClass class's method do_workflow gets an error while doing a workflow

    """
    pass


class MergeAlertsCollectorClassFailure(Exception):
    """

    This exception is used when the CollectorClass class's method merge_alerts gets an error while merging all alerts

    """
    pass


class SendAlertsCollectorClassFailure(Exception):
    """

    This exception is used when the CollectorClass class's method send_combined_alerts gets an error while sending
    combined alerts

    """
    pass


def main():
    """
    Main Function
    ====================
    
    Main function to call appropriate functions to 

    """


if __name__ == '__main__':
    main()
