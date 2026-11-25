# -*- coding: UTF-8 -*-
"""
Initialization For Database Operations
===========================================

This Initialization module imports the necessary functions and modules, create mongodb url connection string.

This script requires that the following packages be installed within the Python
environment you are running this script in.

    * logging - To perform logging operations.
"""

# Standard library imports
import logging

# Related third party imports

# Local application/library specific imports
from collector_app.datatool.env_util import get_env_variables


__author__ = "smt18m005@iiitdm.ac.in"

LOGGER = logging.getLogger(__name__)

# Get environment variables
env_vars = get_env_variables()

# MongoDB URL from environment variables
MONGODB_URL = env_vars.mongodb_url

# TimescaleDB URL constructed from environment variables
TIMESCALEDB_URL = f"postgres://{env_vars.timescaledb_user}:{env_vars.timescaledb_password}@{env_vars.timescaledb_host}:{env_vars.timescaledb_port}/{env_vars.timescaledb_database}"

# Parameter config path
PARAMETER_CONFIG = "/home/tnga_iot/iiot_project/codes/collector_system/main_codes/collector_main/configs/"
