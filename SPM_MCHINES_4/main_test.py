#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Main Module for the Monitoring Application
===============================================

Module for starting point of the Monitoring application

This script requires the following modules be installed in the python environment
    Standard Library
    =================

    * logging - To perform logging operations
    * pathlib - To work with files and directories

    This script contains the following function
    * main - Main function to call appropriate functions to test out monitoring function

"""

# Standard library imports
import logging
import time
from pathlib import Path

# Related third party imports

# Local application/library specific imports
from app.utils.config_helper import configure_logging
from app.database.crud_operations import read_last_creation_time

from app.initialization_services.initial_setup import last_creation_time_setup
from app.file_system_operation.directory_monitoring import start_monitoring

from app.utils import INPUT_ARGUMENTS
from app.database.crud_operations import main as crud_operations
from app.data_transformation_services.tranformation_functions import main as transformation_operations
from app.file_system_operation.directory_monitoring import main as directory_monitoring

__author__ = "smt18m005@iiitdm.ac.in"

LOGGER = logging.getLogger(__name__)


def main():
    """
    MAIN
    ========

    Main function to call appropriate functions to start monitoring the directories

    :return: Nothing
    """

    # Configuring logger
    configure_logging()

    # Setting up the directory to monitor
    directory = Path(INPUT_ARGUMENTS.directory)

    #crud_operations()
    #transformation_operations()
    directory_monitoring()


if __name__ == '__main__':
    # The main function  will be run when the whole script is run as main script
    main()
