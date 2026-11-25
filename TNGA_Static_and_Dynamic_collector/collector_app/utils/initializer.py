"""
Initializer Module
==================

This module contains functions for initializing the project, including
logger configuration and other setup tasks.

Functions
---------
initialize_project : function
    Initialize the project.

Classes
-------
MyClass : SomeClass
    A class for handling special cases in project initialization.
"""

# Standard library imports
import json
import logging.config
import sys

# Local application/library specific imports
from collector_app.datatool.env_util import get_env_variables
from collector_app.database.orm.pony_orm_connector import initialize_pony
from collector_app.database.orm.pony_entity_model import generate_pony_mapping

__author__ = "Praveen Kumar G"

LOGGER = logging.getLogger(__name__)


def load_config_data(filepath):
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
        raise Exception(error)
    except Exception as error:
        LOGGER.exception(error)
        raise Exception(error)


def configure_logging(filepath):
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


def initialize_app(filepath: str):
    """
    Initialize the Application.

    Parameters
    ----------
    filepath : str
        The path to the JSON configuration file.

    Returns
    -------
    None
        Nothing.
    """

    try:

        configure_logging(filepath)

        initialize_pony()

        generate_pony_mapping(create_tables=False)

    except Exception as error:
        LOGGER.error(f"Error While Initializing the Application: \n {error}")
        sys.exit(1)
