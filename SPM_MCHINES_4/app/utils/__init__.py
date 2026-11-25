# -*- coding: UTF-8 -*-
"""
Initialization For Utils Package
===========================================

This Initialization module imports the necessary functions from the modules within this package
"""

# Importing necessary modules and functions to be used by modules using this package
from app.utils.input_getter import get_input_arguments

DEFAULT_LOGGER_PATH = "./configs/log.json"
DEFAULT_DB_CREDENTIALS_PATH = "./configs/credentials.json"

INPUT_ARGUMENTS = get_input_arguments()
