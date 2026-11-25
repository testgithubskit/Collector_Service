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
from app.utils.check_mount import check_for_mount_drive, mount_shared_drive

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

    # Setting up initial local db for storing local creation time
    last_creation_time_setup()

    # Reading the last created time from db
    last_creation_time = read_last_creation_time()

    # Setting up the directory to monitor
    directory = Path(INPUT_ARGUMENTS.directory)

    if INPUT_ARGUMENTS.os == "linux":
        # If the script is being run of production linux server do the following
        while True:
            try:
                LOGGER.info("Checking for shared drive")
                if not check_for_mount_drive(directory):
                    LOGGER.info("Mounting drive")
                    # If the shared folder is not mounted as a drive, mount it
                    mount_shared_drive()
                    LOGGER.info("Checking for shared drive, again!")
                    if check_for_mount_drive(directory):
                        # If the previous attempt to mount was successful, break from the loop
                        LOGGER.info("Mounted the shared folder drive")
                        break
                    # If previous attempt to mount was not successful, sleep for 5 sec and repeat the process
                    LOGGER.error("Not Able to mount the shared folder, check the network")
                    time.sleep(5)
                else:
                    # If in case it is already mounted, break from the loop
                    LOGGER.info("Already Mounted")
                    break
            except Exception as error:
                LOGGER.error(error)
                LOGGER.info("Sleeping for 5 sec...")
                time.sleep(5)

    # Starting the monitoring applications
    start_monitoring(directory, last_creation_time)


if __name__ == '__main__':
    # The main function  will be run when the whole script is run as main script
    main()
