import logging
import os


def setup_logger():

    # Create a logger
    logger = logging.getLogger('tiei_iiot')
    logger.setLevel(logging.DEBUG)

    # Create handlers for info and error logs
    info_handler = logging.FileHandler('logs/INFO.log')
    info_handler.setLevel(logging.INFO)

    error_handler = logging.FileHandler('logs/ERROR.log')
    error_handler.setLevel(logging.ERROR)

    # Create console handler for terminal output
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # Create formatters and add them to handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    info_handler.setFormatter(formatter)
    error_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Add handlers to the logger
    logger.addHandler(info_handler)
    logger.addHandler(error_handler)
    logger.addHandler(console_handler)

    return logger


LOG = setup_logger()
