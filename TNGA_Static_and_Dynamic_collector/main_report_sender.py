#!/usr/bin/python
# -*- coding: utf-8 -*-
"""

MAIN REPORT SENDER
==========================

Module for starting point of the Collector application

This script requires the following modules be installed in the python environment

    Standard Library
    =================

    * logging - To perform logging operations
    * time - To perform operation related to date and time objects

    This script contains the following function

    * main - Main function to call appropriate functions to start collecting data from MtLinki

"""

# Standard library imports
import logging
import time

# Related third party imports

# Local application/library specific imports
from collector_app.utils.config_helper import configure_logging
from collector_app.report_manager.email_sender import send_mail

__author__ = "smt18m005@iiitdm.ac.in"

LOGGER = logging.getLogger(__name__)


def main():
    """

    MAIN
    ========

    Main function to call appropriate functions to start report sender service

    :return: Nothing

    """

    # Configuring logger
    configure_logging()

    for _ in range(2):
        send_mail()
        time.sleep(5)


if __name__ == '__main__':
    # The main function  will be run when the whole script is run as main script
    main()
