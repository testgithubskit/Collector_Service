#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
DATABASE UTILITY FUNCTIONS
================================

Module that has utility functions for database operations

This script requires the following modules be installed in the python environment
    * logging - To perform logging operations.
    * motor - To perform database connection operation in asynchronous way.

This script contains the following function
    * connect_to_mongo - Function that connects to mongodb by creating a client at the start of the application.
    * close_mongo_connection - Function that destroys the connection to mongodb by closing the mongodb client.
"""

# Standard library imports
import logging
from contextlib import closing
import sqlite3
# Related third party imports

# Local application/library specific imports
from ..database import SQLITE3_URL

__author__ = "smt18m005@iiitdm.ac.in"

LOGGER = logging.getLogger(__name__)
