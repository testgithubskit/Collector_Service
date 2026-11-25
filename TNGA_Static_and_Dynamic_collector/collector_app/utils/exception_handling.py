# -*- coding: utf-8 -*-
"""
Exception Handling Utilities
=================================

This module consist of function used as a decorator throughout this project to handle exception

This script requires the following modules be installed in the python environment
    * logging - To perform logging operations
    * functools - The functools module is for higher-order functions: functions that act on or return other functions
                 here used for updating the decorator functions variable namespace (read more by looking for
                 @functools.wraps(func) in google)

This script contains the following function
    * exception_handler - The main function which captures specific exceptions and logs them
"""

# Standard imports
import logging
import functools


__author__ = "smt18m005@iiitdm.ac.in"

LOGGER = logging.getLogger(__name__)


def exception_handler(func):
    """

    The Exception handling function used as decorator throughout the project

    :param func: The function that needs to be decorated
    :type func: function

    :return: The wrapped up function
    :rtype: function

    """

    @functools.wraps(func)
    def wrapper_exception_handler(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except RuntimeError as error:
            LOGGER.error(f"Runtime Error: {error}")
        except KeyError as error:
            LOGGER.error(f"KeyWord error: {error}")
        except Exception as error:
            LOGGER.error(error)

    return wrapper_exception_handler
