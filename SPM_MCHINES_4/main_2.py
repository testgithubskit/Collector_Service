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

from app.file_system_operation.directory_monitoring import start_monitoring, start_monitoring_spm

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

    # Setting up the directory to monitor
    directory = Path(INPUT_ARGUMENTS.directory)
    directory_copy = Path(INPUT_ARGUMENTS.directory_copy) 
    ip_add = INPUT_ARGUMENTS.ip_address
    mount_loc = INPUT_ARGUMENTS.mount_location
    if INPUT_ARGUMENTS.os == "linux" and not INPUT_ARGUMENTS.skip_mount:
        # If the script is being run of production linux server do the following
        while True:
            try:
                LOGGER.info("Checking for shared drive")
                if not check_for_mount_drive(directory, ip_address=ip_add, mount_location=mount_loc):
                    LOGGER.info("Mounting drive")
                    # If the shared folder is not mounted as a drive, mount it
                    mount_shared_drive(ip_address=ip_add, mount_location=mount_loc)
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
    elif INPUT_ARGUMENTS.skip_mount:
        LOGGER.info("Skipping mount operations (Docker mode)")

    # Starting the monitoring application
    start_monitoring_spm(
        directory,
        machine_id=INPUT_ARGUMENTS.machine_id,
        file_counter=INPUT_ARGUMENTS.file_counter,
        date_str=INPUT_ARGUMENTS.date
    )


if __name__ == '__main__':
    # The main function  will be run when the whole script is run as main script
    main()
