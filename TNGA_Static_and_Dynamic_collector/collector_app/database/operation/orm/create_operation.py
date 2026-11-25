"""
ORM Create Operation Module
===========================

The `create_operation` module within the `orm` subpackage provides functions to create records in the database
using Object-Relational Mapping (ORM) tools. It includes functionalities to insert new records into the database
tables represented by ORM entities.

Functions
---------
- `insert_movies_data`: Function to insert movie records in the database from a given list of data.
- `create_product_record`: Function to create a new product record in the database.
- `create_order_record`: Function to create a new order record in the database.
- ... (add more functions as needed)

"""

# Standard library imports
import logging
import time

# Related third-party imports
from pony.orm import db_session, commit

# Local module imports
import collector_app.database.orm.pony_entity_model as pony_models
from collector_app.database.error.exception_utils import db_exception_handler

LOGGER = logging.getLogger(__name__)


@db_session
@db_exception_handler
def insert_customer(_data: dict):
    LOGGER.debug("Inserting Customer")

    commit()

    return


def main():

    start_time = time.time()  # Record the start time

    end_time = time.time()  # Record the end time
    elapsed_time = end_time - start_time

    LOGGER.info(f"Inserted Movies in {elapsed_time:.2f} seconds")


if __name__ == "__main__":
    main()
