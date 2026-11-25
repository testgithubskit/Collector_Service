# -*- coding: UTF-8 -*-
"""
Initialization For Database Operations
===========================================

This Initialization module imports the necessary functions and modules, create mongodb url connection string.

This script requires that the following packages be installed within the Python
environment you are running this script in.

    * logging - To perform logging operations.
    * os - To interact with os.
    * databases - To create database url using mongodb connection string.
"""

# Standard library imports

# Related third party imports
import yagmail

EMAIL_REPORT_ROOT_DIRECTORY = "./output/email_reports/"

EMAIL_REPORT_ROOT_DIRECTORY_TEMP = "./output/email_reports_temporary/"

MAIL_SERVER_HOST = 'smtp.gmail.com'
MAIL_SERVER_PORT = 587

SENDER_EMAIL = "cmti.unofficial@gmail.com"
SENDER_PASSWORD = "xbuwypsvsphdbdvu"

RECEIVER_EMAIL = "praveen06061995@gmail.com"
EMAIL_SERVER = yagmail.SMTP(SENDER_EMAIL, SENDER_PASSWORD)

EMAIL_MESSAGE = "New Alerts generated, please download the report"
