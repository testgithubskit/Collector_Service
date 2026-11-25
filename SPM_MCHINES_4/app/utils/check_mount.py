
#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
CHECK FOR SHARED FOLDER
================================

Module for checking and mounting windows shared folder

This script requires the following modules be installed in the python environment
    * logging - to perform logging operations

This script contains the following function
    * main - main function to call appropriate functions to find the contours in the video
"""

# Standard library imports
import logging
import os
from pathlib import Path
import subprocess

# Related third party imports


# Local application/library specific imports


__author__ = "smt18m005@iiitdm.ac.in"

LOGGER = logging.getLogger(__name__)


def check_for_mount_drive(directory: Path, ip_address: str="//10.82.126.72/jop140", mount_location: str="/mnt/spm_journal_grinding/jop_140"):
    """

    :return:
    :rtype:
    """

    command_to_mount = ["sudo", "mount", "-t", "cifs", "-o", "username=tnga_iot,password=Toyota_2022",
                        f"{ip_address}",f"{mount_location}"]
    command_to_ping = ["ping", "-c", "1", "10.82.126.72"]
    host_status = subprocess.call(command_to_ping)
    if host_status != 0:
        raise ConnectionError("Host 10.82.126.72 is unreachable, try again!")

    if not os.path.exists(directory):
        return False
    return True


def mount_shared_drive(ip_address: str="//10.82.126.72/jop140", mount_location: str="/mnt/spm_journal_grinding/jop_140"):
    """

    :return:
    """

    command_to_mount = ["sudo", "mount", "-t", "cifs", "-o", "username=tnga_iot,password=Toyota_2022",
                        f"{ip_address}",f"{mount_location}"]

    command_to_ping = ["ping", "-c", "1", "10.82.126.72"]

    host_status = subprocess.call(command_to_ping)
    if host_status != 0:
        raise ConnectionError("Host 10.82.126.72 is unreachable, try again!")
    result = subprocess.run(command_to_mount, input=b"ubuntu")
    LOGGER.info(f"Executed Command with result: {result}")


def main():
    """
    Main Function
    ====================
    
    Main function to call appropriate functions to 

    """


if __name__ == '__main__':
    main()
