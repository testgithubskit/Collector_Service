import logging
import os


class InfoFilter(logging.Filter):
    """Filter to allow only INFO level messages."""

    def filter(self, record):
        return record.levelno == logging.INFO


class ErrorFilter(logging.Filter):
    """Filter to allow only ERROR and above level messages."""

    def filter(self, record):
        return record.levelno >= logging.ERROR


def setup_logger(plant):
    # Create a logger
    logger = logging.getLogger(f'{plant}')
    logger.setLevel(logging.DEBUG)

    # Create handlers for info and error logs
    info_handler = logging.FileHandler(f'logs/INFO_{plant}.log')
    info_handler.setLevel(logging.INFO)

    error_handler = logging.FileHandler(f'logs/ERROR_{plant}.log')
    error_handler.setLevel(logging.ERROR)

    # Apply filters to handlers
    info_handler.addFilter(InfoFilter())
    error_handler.addFilter(ErrorFilter())

    # Create formatters and add them to handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    info_handler.setFormatter(formatter)
    error_handler.setFormatter(formatter)

    # Add handlers to the logger
    logger.addHandler(info_handler)
    logger.addHandler(error_handler)

    return logger


