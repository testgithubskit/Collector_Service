"""
Database Exception Utilities
===========================

The `exception_utils` module within the `error` subpackage provides functions to handle exceptions while handling
database operations

Functions
---------
- `db_exception_handler`: Function to insert movie records in the database from a given list of data.
- `create_product_record`: Function to create a new product record in the database.
- `create_order_record`: Function to create a new order record in the database.
- ... (add more functions as needed)

"""

# Standard library imports
import logging
from functools import wraps

# Related third-party imports
from pony.orm.core import TransactionIntegrityError, OperationalError, DatabaseError


LOGGER = logging.getLogger(__name__)


def db_exception_handler(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            return result
        except TransactionIntegrityError as error:
            LOGGER.error(f"Error with database, the data might already exist : \n {error}")
            raise Exception(error)
        except OperationalError as error:
            LOGGER.error(f"Error during operation with database : \n {error}")
            raise Exception(error)
        except DatabaseError as error:
            LOGGER.error(f"Possible syntax error issue with query : \n {error}")
            raise Exception(error)
        except Exception as error:
            LOGGER.error(f"Unknown error : \n {error}")
            raise Exception(error)

    return wrapper
