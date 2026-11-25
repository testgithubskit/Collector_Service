# -*- coding: utf-8 -*-
"""
Command Line Input Getter
============================
Main Module for getting the command line arguments

This script requires the following modules be installed in the python environment
    * argparse - to handle command line arguments

This script contains the following function
    * get_input_arguments - to get the command line arguments
"""
# Built-in imports
import argparse


def get_input_arguments() -> argparse.Namespace:
    """
    INPUT GETTER
    ===============

    Function to get the input arguments from command line

    :return: args - arguments from the command line
    """

    my_parser = argparse.ArgumentParser(allow_abbrev=False)
    # New optional date filter (YYYY-MM-DD)
    my_parser.add_argument('--date', action='store', type=str, required=False,
                            help='Process files created on/after this date (YYYY-MM-DD)')
    my_parser.add_argument('--logfile', action='store', type=str, required=False)
    my_parser.add_argument('--user', action='store', type=str, required=True)
    my_parser.add_argument('--host', action='store', type=str, required=True)
    my_parser.add_argument('--password', action='store', type=str, required=True)
    my_parser.add_argument('--database', action='store', type=str, required=True)
    my_parser.add_argument('--os', action='store', type=str, required=True)
    my_parser.add_argument('--directory', action='store', type=str, required=True)
    my_parser.add_argument('--machine_id', action='store', type=int, required=False)
    my_parser.add_argument('--database_name', action='store', type=str, required=False)
    my_parser.add_argument('--ip_address', action='store', type=str, required=False)
    my_parser.add_argument('--mount_location', action='store', type=str, required=False)
    my_parser.add_argument('--directory_copy', action='store', type=str, required=True)
    my_parser.add_argument('--skip_mount', action='store_true', required=False, help='Skip mount operations for Docker')
    my_parser.add_argument('--file_counter', action='store', type=int, required=False, default=50,
                            help='Number of files to skip between each processing cycle (default: 50)')

    args = my_parser.parse_args()
    return args
