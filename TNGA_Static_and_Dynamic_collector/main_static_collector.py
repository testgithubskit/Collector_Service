#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Main Module for the Dynamic Collector Application
=====================================================

Module for starting point of the Collector application

This script requires the following modules be installed in the python environment

    Standard Library
    =================

    * logging - To perform logging operations

    This script contains the following function
    * main - Main function to call appropriate functions to start collecting data from MtLinki

"""

# Standard library imports
import logging

# Related third party imports

# Local application/library specific imports
from collector_app.collector_classes.collector_classes_module import CollectorClass
from collector_app.utils.initializer import initialize_app

__author__ = "smt18m005@iiitdm.ac.in"

LOGGER = logging.getLogger(__name__)


def main():
    """
    MAIN
    ========

    Main function to call appropriate functions to start collecting data from MtLinki

    :return: Nothing
    """

    # Configuring logger
    initialize_app(filepath="./configs/log_static.json")

    collector_system = CollectorClass(read_cycle_time=1)
    collector_system.load_parameters()
    collector_system.start_collector()


if __name__ == '__main__':
    # The main function  will be run when the whole script is run as main script
    main()
