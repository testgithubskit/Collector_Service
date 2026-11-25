#!/usr/bin/python
# -*- coding: utf-8 -*-
"""

================================

Module for  application to

This script requires the following modules be installed in the python environment
    * logging - to perform logging operations

This script contains the following function
    * main - main function to call appropriate functions to find the contours in the video
"""

# Standard library imports
import logging
from contextlib import closing
import sqlite3
import time
# Related third party imports


# Local application/library specific imports
from app.database import SQLITE3_URL

__author__ = "smt18m005@iiitdm.ac.in"

LOGGER = logging.getLogger(__name__)


def last_creation_time_setup(sql_url=SQLITE3_URL):
    """

    :return:
    :rtype:
    """
    current_epoch = time.time()
    minutes_to_add = 2
    seconds_to_add = minutes_to_add * 60
    future_epoch = current_epoch + seconds_to_add

    sql_statement_for_table_creation = "CREATE TABLE last_time (id INTEGER, time REAL)"
    sql_statement_for_data_insertion = f"INSERT INTO last_time VALUES (1, {future_epoch})"
    LOGGER.info(f"future time: {future_epoch}")

    LOGGER.info("Connecting to DB")
    LOGGER.info(sql_url)
    try:
        with closing(sqlite3.connect(sql_url)) as connection:
            with closing(connection.cursor()) as cursor:
                cursor.execute(sql_statement_for_table_creation)
                cursor.execute(sql_statement_for_data_insertion)
                connection.commit()
        LOGGER.info("Created, and Update Time with sample value")
    except Exception as error:
        LOGGER.error(error)


def main():
    """
    Main Function
    ====================
    
    Main function to call appropriate functions to 

    """

    last_creation_time_setup()


if __name__ == '__main__':
    main()
