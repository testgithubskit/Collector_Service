#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Logging Configuration
================================

Main Module for configuring logger

This script requires the following modules be installed in the python environment
    * logging - To perform logging operations
    * json - To load json files

This script contains the following function
    * configure_logging - To configure logging
    * load_database_credentials - To load database credentials file
"""

# Standard library imports
import logging.config
import json

# Local application/library specific imports
from ..utils import DEFAULT_LOGGER_PATH, DEFAULT_DB_CREDENTIALS_PATH
from collector_app.exception_helper.custom_exception_classes import LoadConfigFailure

__author__ = "smt18m005@iiitdm.ac.in"

LOGGER = logging.getLogger(__name__)


def load_config_data(filepath: str = DEFAULT_LOGGER_PATH):
    """
    Function to configure logging
    ==================================

    :param filepath: The file path for the logger configuration file
    :type filepath: str

    :return: Nothing
    """
    try:
        with open(filepath, 'r') as file_object:
            config_data = json.load(file_object)

        return config_data
    except FileNotFoundError as error:
        LOGGER.exception(error)
        raise LoadConfigFailure(error)
    except Exception as error:
        LOGGER.exception(error)
        raise LoadConfigFailure(error)


def configure_logging(filepath: str = DEFAULT_LOGGER_PATH):
    """
    Function to configure logging
    ==================================

    :param filepath: The file path for the logger configuration file
    :type filepath: str

    :return: Nothing
    :rtype: None
    """

    config_data = load_config_data(filepath)

    logging.config.dictConfig(config_data)

    LOGGER.info("Configured Logging")


def load_database_credentials(filepath: str = DEFAULT_DB_CREDENTIALS_PATH):
    """
    Function to load database credentials file
    ================================================

    :param filepath: The file path for the database credentials file
    :type filepath: str

    :return: Dictionary consisting of database connection credentials
    :rtype: dict
    """
    try:
        with open(filepath, 'r') as file_object:
            credential_data = json.load(file_object)
    except FileNotFoundError as err:
        LOGGER.error(err)
        raise

    LOGGER.info("Loaded DB credentials file")

    return credential_data
