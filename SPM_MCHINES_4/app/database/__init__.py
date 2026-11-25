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
from pathlib import Path
from app.utils import INPUT_ARGUMENTS
# Related third party imports


__author__ = "smt18m005@iiitdm.ac.in"

LOGGER = logging.getLogger(__name__)

SQLITE3_URL = Path("./inputs/db_lite/data/creation_time.db")
SQLITE3_URL_2 = Path("./inputs/db_lite/data/creation_time_spm_2_grinding_machine.db")
SQLITE3_URL_3 = Path("./inputs/db_lite/data/creation_time_spm_3_grinding_machine.db")
SQLITE3_URL_4 = Path("./inputs/db_lite/data/creation_time_spm_4_grinding_machine.db")
SQLITE3_URL_5 = Path("./inputs/db_lite/data/creation_time_spm_5_grinding_machine.db")

SQL_DIC = {"jop105": SQLITE3_URL_2, "jop130": SQLITE3_URL_3, "jop140": SQLITE3_URL_4, "spm_5": SQLITE3_URL_5}

# TIMESCALEDB_URL = "postgres://postgres:password@localhost:5432/tiei_test"
# TIMESCALEDB_URL = "postgres://postgres:siri2251105@172.18.100.156:5432/Toyota_server"

TIMESCALEDB_URL = f"postgres://{INPUT_ARGUMENTS.user}:{INPUT_ARGUMENTS.password}@{INPUT_ARGUMENTS.host}" \
                  f":5435/{INPUT_ARGUMENTS.database}"
