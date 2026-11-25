#!/usr/bin/python
# -*- coding: utf-8 -*-
"""

COMMON QUERY TEMPLATES
===========================

Module that consist of template for common queries

This script requires the following modules be installed in the python environment

    Standard Library
    =================

    * logging - to perform logging operations
    * re - to perform regex operations
    * datetime - to perform datetime operations

This script contains the following function

    * get_check_new_data_template - This function is used to return the query template that will be used to check
     for new data in the MtLinki
    * get_new_data_template - This function gives the query template to get new data from MtLinki
    * main - main function to call appropriate functions to carry out the required task

"""

# Standard library imports
import logging
import re
import datetime
from datetime import datetime, timezone

# Related third party imports


# Local application/library specific imports


__author__ = "smt18m005@iiitdm.ac.in"

LOGGER = logging.getLogger(__name__)


def get_check_new_data_template(regex_pattern):
    """

    This function is used to return the query template that will be used to check for new data in the MtLinki

    :param regex_pattern: The regex pattern used to filter out signalname
    :type regex_pattern: str

    :return: Returns the aggregation pipeline required for the query
    :rtype: [dict]

    """

    # This query matches the signalname with the given regex ,sorts the data by updatedate field
    # Projects only the updatedate column (and also converts from ISODate format to decimal)
    query_template = [
        {
            '$match': {
                'signalname': {
                    '$regex': re.compile(rf"{regex_pattern}")
                }
            }
        }, {
            '$sort': {
                'updatedate': -1
            }
        }, {
            '$project': {
                'updatedate': {
                    '$toDecimal': '$updatedate'
                },
                '_id': 0
            }
        }, {
            '$limit': 1
        }
    ]

    return query_template


def get_new_data_template(regex_pattern, search_time):
    """

    This function gives the query template to get new data from MtLinki

    :param search_time: The time that will be used to query MtLinki MongoDB (data with updatedate greater than
    this time will be queried)
    :type search_time: datetime.datetime

    :param regex_pattern: The regex pattern used to filter out signalname
    :type regex_pattern: str

    :return: Return the pipeline (Non-aggregator) used to query the database for data
    :rtype: dict
    """

    # Converting the millisecond to seconds by dividing it by 1000
    #search_time = datetime.datetime.utcfromtimestamp(search_time_epoch / 1000)

    # query_template = {'signalname': {'$regex': re.compile(rf"{regex_pattern}")},
    #                   'updatedate': {'$gt': search_time}, "value": {"$ne": None}}

    query_template = {'signalname': {'$regex': re.compile(rf"{regex_pattern}")},
                      'updatedate': {'$gt': search_time}}
    return query_template


def get_dynamic_data_template(machine_name, regex_pattern, search_start_time, search_end_time):
    """

    This function gives the query template to get new data from MtLinki

    :param machine_name:
    :type machine_name:

    :param search_start_time: The time that will be used to query MtLinki MongoDB (data with updatedate greater than
    this time will be queried)
    :type search_start_time: datetime.datetime

    :param search_end_time: The time that will be used to query MtLinki MongoDB (data with updatedate greater than
    this time will be queried)
    :type search_end_time: datetime.datetime

    :param regex_pattern: The regex pattern used to filter out signalname
    :type regex_pattern: str

    :return: Return the pipeline (Non-aggregator) used to query the database for data
    :rtype: dict

    """

    #regex_pattern = "spindleload(?i)"
    #search_start_time = datetime(2022, 6, 17, 10, 55, 0, tzinfo=timezone.utc)
    #search_end_time = datetime(2022, 6, 20, 15, 15, 0, tzinfo=timezone.utc)
    # Converting the millisecond to seconds by dividing it by 1000
    #search_time = datetime.datetime.utcfromtimestamp(search_time_epoch / 1000)
    #machine_name = "T_H_OP180A"

    query_template = [
                        {
                            '$match': {
                                'L1Name': machine_name,
                                'signalname': regex_pattern,
                                'enddate': {
                                    # The end date should be greater than than the updatedate from the
                                    # Program history
                                    '$gt': search_start_time,

                                    # The enddate should be less than or equal to the enddate from the
                                    # Program history
                                    '$lte': search_end_time
                                },
                                'updatedate': {
                                    '$gt': search_start_time
                                },
                                "value": {"$ne": None},
                            }
                        }, {
                            '$sort': {
                                'enddate': 1
                            }
                        }, {
                            '$project': {
                                'signalname': 1,
                                'updatedate': 1,
                                'L1Name': 1,
                                'value': 1,
                                '_id': 0
                            }
                        }
                    ]

    return query_template


def main():
    """
    Main Function
    ====================
    
    Main function to call appropriate functions to out the required task

    """
    pass


if __name__ == '__main__':
    main()
