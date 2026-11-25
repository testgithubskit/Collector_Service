#!/usr/bin/python
# -*- coding: utf-8 -*-
"""

EMAIL SENDER
==================

Module for sending email alerts

This script requires the following modules be installed in the python environment
    Standard Library
    =================

    * logging - to perform logging operations
    * os - to os related operations
    * smtplib - to send email alerts

This script contains the following function
    * main - main function to call appropriate functions to send email alerts

"""

# Standard library imports
import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

# Related third party imports


# Local application/library specific imports
from collector_app.report_manager import SENDER_EMAIL, RECEIVER_EMAIL, SENDER_PASSWORD, MAIL_SERVER_HOST, \
    MAIL_SERVER_PORT, EMAIL_REPORT_ROOT_DIRECTORY_TEMP, EMAIL_MESSAGE

__author__ = "smt18m005@iiitdm.ac.in"

LOGGER = logging.getLogger(__name__)


def send_mail():
    """

    Function to send emails for new alerts generated

    :return: Nothing
    :rtype: None
    """

    try:
        message = MIMEMultipart()

        message['To'] = RECEIVER_EMAIL
        message['From'] = SENDER_EMAIL
        message['subject'] = "NEW MACHINE ALERT"

        message.attach(MIMEText(EMAIL_MESSAGE, 'plain'))

        #file_path = "D:\\PS-CMTI\\Codes\\PycharmProjects\\TIEI Master\\collector\\
        # collector_main\\output\\email_reports\\"

        reports = os.listdir(EMAIL_REPORT_ROOT_DIRECTORY_TEMP)
        attachments = [(report, EMAIL_REPORT_ROOT_DIRECTORY_TEMP + report) for report in reports]

        for attachment in attachments:

            with open(attachment[1], 'rb') as report_file:

                file = MIMEBase('application', 'octet-stream')
                file.set_payload(report_file.read())
                encoders.encode_base64(file)
                file.add_header('Content-Disposition', "attachment; filename= %s" % attachment[0])

                message.attach(file)

        email_server = smtplib.SMTP(MAIL_SERVER_HOST, MAIL_SERVER_PORT)
        email_server.ehlo()
        email_server.starttls()
        email_server.ehlo()
        email_server.login(SENDER_EMAIL, SENDER_PASSWORD)
        email_server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, message.as_string())
        email_server.quit()
    except Exception as error:
        LOGGER.exception("Error", error.args[0])
        return

    # The reports will be deleted only if they were successfully sent as email
    try:
        for attachment in attachments:
            os.remove(attachment[1])
    except Exception as error:
        LOGGER.exception("Error", error.args[0])


def main():
    """
    Main Function
    ====================
    
    Main function to call appropriate functions to 

    """

    send_mail()


if __name__ == '__main__':
    main()
