#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
REPORT SUMMARY GENERATOR
================================

Module for generating excel report for anomalies

This script requires the following modules be installed in the python environment
    * logging - to perform logging operations

This script contains the following function
    * main - main function to call appropriate functions to find the contours in the video
"""

# Standard library imports
import logging
from datetime import datetime

# Related third party imports
import xlsxwriter

__author__ = "smt18m005@iiitdm.ac.in"

LOGGER = logging.getLogger(__name__)


def create_excel_report(file_location: str, machine_name: str, static_data, dynamic_data):
    """
    Function to create a full report

    :return:
    :rtype:
    """

    workbook = xlsxwriter.Workbook(file_location)
    # end_time = datetime.now(pytz.utc)
    #end_time = datetime(2022, 9, 7, 6, 30, 0)
    # start_time = end_time - timedelta(hours=4)
    #start_time = datetime(2022, 9, 7, 6, 20, 0)

    cell_format = workbook.add_format()

    cell_format.set_align('center')
    cell_format.set_align('vcenter')

    # Create a format to use in the merged range.
    merge_format = workbook.add_format({
        'bold': 5,
        'border': 3,
        'align': 'center',
        'valign': 'vcenter',
        'fg_color': 'yellow'})

    worksheet = workbook.add_worksheet("new_alerts_data")

    worksheet.set_column(0, 0, 15, cell_format)
    worksheet.set_column(1, 2, 25, cell_format)
    worksheet.set_column(3, 3, 65, cell_format)
    worksheet.set_column(4, 4, 15, cell_format)
    worksheet.set_column(5, 5, 20, cell_format)
    worksheet.set_column(6, 8, 15, cell_format)

    # Merge cells
    worksheet.merge_range('A1:J1', 'Merged Range', merge_format)

    worksheet.write('A1', f'TNGA Machining Critical Abnormality Report for {machine_name}')

    worksheet.merge_range('A3:D3', 'Merged Range', merge_format)
    worksheet.write('A3', 'Static Parameters')

    start_cell_static = "B4"

    if not static_data and not dynamic_data:
        return
    length_of_static_data = 1

    if static_data:
        length_of_static_data = len(static_data)

        end_cell_static = "H" + str(4 + length_of_static_data)
        worksheet.add_table(f'{start_cell_static}:{end_cell_static}',
                            {'data': static_data,
                             'columns': [{'header': 'S.No'},
                                         {'header': 'Time'},
                                         {'header': 'Parameter'},
                                         {'header': 'Value'},
                                         {'header': 'Status'},
                                         {'header': 'Warning Limit'},
                                         {'header': 'Critical Limit'}]})

    worksheet.merge_range(f'A{4 + length_of_static_data + 4}:D{4 + length_of_static_data + 4}',
                          'Merged Range', merge_format)

    worksheet.write(f'A{4 + length_of_static_data + 4}', 'Dynamic Parameters')

    if dynamic_data:
        worksheet.add_table(f'B{4 + length_of_static_data + 5}:E{4 + length_of_static_data + 5 + len(dynamic_data)}',
                            {'data': dynamic_data,
                             'columns': [{'header': 'S.No'},
                                         {'header': 'Time'},
                                         {'header': 'Parameter'},
                                         {'header': 'Status'}]})

    workbook.close()
