import os
import pandas as pd
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from datetime import datetime, timezone, timedelta
from openpyxl.cell.cell import MergedCell
from logs.logger_module import LOG

# IST timezone (UTC+5:30)
IST_OFFSET = timedelta(hours=5, minutes=30)
TZ_IST = timezone(IST_OFFSET)


def create_excel_report(access_log_df, unassigned_df, assigned_df, disconnection_df, recent_disconnections_df, output_filename):
    """
    Creates an Excel report with Access Log, Abnormality Summary, and Disconnection Summary sheets.

    Parameters:
    access_log_df: pandas DataFrame with columns
    unassigned_df: pandas DataFrame with columns
    assigned_df: pandas DataFrame with columns
    disconnection_df: pandas DataFrame with columns
    recent_disconnections_df: pandas DataFrame with recent disconnections (last 30 min before report hour)
    output_filename: String, name of the output Excel file
    """
    try:
        LOG.info(f"Starting Excel report generation: {output_filename}")
        LOG.info(f"Access log DataFrame shape: {access_log_df.shape}")
        LOG.info(f"Unassigned DataFrame shape: {unassigned_df.shape}")
        LOG.info(f"Assigned DataFrame shape: {assigned_df.shape}")
        LOG.info(f"Disconnection DataFrame shape: {disconnection_df.shape}")
        LOG.info(f"Recent Disconnections DataFrame shape: {recent_disconnections_df.shape}")

        wb = Workbook()
        LOG.info("Workbook created successfully")

        create_access_log_sheet(wb, access_log_df)
        LOG.info("Access Log sheet created successfully")

        create_abnormality_summary_sheet(wb, unassigned_df, assigned_df)
        LOG.info("Abnormality Summary sheet created successfully")

        create_disconnection_sheet(wb, disconnection_df, recent_disconnections_df)
        LOG.info("Disconnection Summary sheet created successfully")

        save_workbook(wb, output_filename)
        LOG.info(f"Excel report saved successfully: {output_filename}")

    except Exception as e:
        LOG.error(f"Error creating Excel report: {e}")
        raise


def create_access_log_sheet(wb, df_access_log):
    ws = wb.active
    ws.title = 'Access Log'

    # Add initial rows for spacing
    [ws.append([]) for _ in range(4)]

    # Append DataFrame rows to the sheet
    for r in dataframe_to_rows(df_access_log, index=False, header=True):
        ws.append(r)
        break

    last_accessed_row = ws.max_row + 1
    ws.merge_cells(start_row=last_accessed_row, start_column=1, end_row=last_accessed_row, end_column=ws.max_column)
    ws.cell(row=last_accessed_row, column=1).value = "Last User Access Record"
    ws.row_dimensions[last_accessed_row].height = 22

    first_entry_row = 0
    if not df_access_log.empty:
        first_entry_row = last_accessed_row + 1
        ws.append(df_access_log.iloc[0].tolist())
        ws.row_dimensions[first_entry_row].height = 20
    if len(df_access_log) > 1:
        temp_bool = True
    else:
        temp_bool = False
    today_logins_row = first_entry_row + 1
    ws.merge_cells(start_row=today_logins_row, start_column=1, end_row=today_logins_row, end_column=ws.max_column)
    ws.cell(row=today_logins_row,
            column=1).value = "Today's User Access Records" if temp_bool else "No user has accessed the dashboard today!"

    ws.row_dimensions[today_logins_row].height = 22

    if len(df_access_log) > 1:
        for r in dataframe_to_rows(df_access_log.iloc[1:], index=False, header=False):
            ws.append(r)

    style_sheet_0(ws, start_row=5, start_col=1, end_row=ws.max_row, end_col=6, temp=temp_bool)
    auto_adjust_column_widths(ws)

    add_header(ws, 'Toyota IIoT-Dashboard: Daily Access Log', 'A1:F1')
    add_timestamp(ws, 'A2:F2')

    ws.row_dimensions[4].height = 20


def create_abnormality_summary_sheet(wb, unassigned_df, assigned_df):
    ws = wb.create_sheet(title="Abnormality Summary")

    ulen = len(unassigned_df)

    [ws.append([]) for i in range(5)]
    add_section(ws, 'UNASSIGNED', 'A5:F5', unassigned_df, start_row=6)

    [ws.append([]) for i in range(4)]
    add_section(ws, 'ASSIGNED', f'A{10 + ulen}:K{10 + ulen}', assigned_df, start_row=11 + ulen)

    auto_adjust_column_widths(ws)

    add_header(ws, 'Toyota IIoT-Dashboard: Abnormality Summary', 'A1:K1')
    add_timestamp(ws, 'A2:K2')


def create_disconnection_sheet(wb, df_disconn, recent_disconnections_df):
    ws = wb.create_sheet(title="Disconnection Summary")

    LOG.info(f"Creating disconnection sheet with DataFrame shape: {df_disconn.shape}")
    LOG.info(f"Recent disconnections DataFrame shape: {recent_disconnections_df.shape}")

    # Add spacing at the top
    [ws.append([None]) for _ in range(6)]

    # Add KPI Summary Block
    total_freq = int(df_disconn['Disconnection Frequency'].sum()) if not df_disconn.empty else 0
    total_minutes = df_disconn['Total Downtime (Minutes)'].sum() if not df_disconn.empty else 0.0
    total_seconds = int(total_minutes * 60)
    hours = total_seconds // 3600
    mins = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    total_hhmmss = f"{hours:02d}:{mins:02d}:{secs:02d}"
    total_disconnected_machines = len(df_disconn) if not df_disconn.empty else 0

    # Write KPI values and labels - REORDERED: Machines, Events, Downtime
    ws.merge_cells('A4:C4')
    ws['A4'] = "Total Disconnected Machines"
    ws.merge_cells('A5:C5')
    ws['A5'] = total_disconnected_machines

    ws.merge_cells('D4:F4')
    ws['D4'] = "Total Disconnection Events"
    ws.merge_cells('D5:F5')
    ws['D5'] = total_freq

    ws.merge_cells('G4:I4')
    ws['G4'] = "Total Overall Downtime (HH:MM:SS)"
    ws.merge_cells('G5:I5')
    ws['G5'] = total_hhmmss

    # Styling the KPI blocks
    kpi_title_font = Font(name='Aptos', size=11, bold=True, color='555555')
    kpi_value_font = Font(name='Aptos', size=16, bold=True, color='000000')
    kpi_fill = PatternFill(start_color='EAEAEA', end_color='EAEAEA', fill_type='solid')
    thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))

    # Style A4:C4 and A5:C5
    for row in range(4, 6):
        for col in range(1, 4):
            cell = ws.cell(row=row, column=col)
            cell.fill = kpi_fill
            cell.border = thin_border
            cell.alignment = Alignment(horizontal='center', vertical='center')
    ws['A4'].font = kpi_title_font
    ws['A5'].font = kpi_value_font

    # Style D4:F4 and D5:F5
    for row in range(4, 6):
        for col in range(4, 7):
            cell = ws.cell(row=row, column=col)
            cell.fill = kpi_fill
            cell.border = thin_border
            cell.alignment = Alignment(horizontal='center', vertical='center')
    ws['D4'].font = kpi_title_font
    ws['D5'].font = kpi_value_font

    # Style G4:I4 and G5:I5
    for row in range(4, 6):
        for col in range(7, 10):
            cell = ws.cell(row=row, column=col)
            cell.fill = kpi_fill
            cell.border = thin_border
            cell.alignment = Alignment(horizontal='center', vertical='center')
    ws['G4'].font = kpi_title_font
    ws['G5'].font = kpi_value_font

    ws.row_dimensions[4].height = 20
    ws.row_dimensions[5].height = 30

    # Add Recent Disconnections Table (last 30 min before report hour)
    if not recent_disconnections_df.empty:
        # Add spacing before recent disconnections table
        [ws.append([None]) for _ in range(2)]
        
        # Add section header
        recent_header_row = ws.max_row + 1
        ws.merge_cells(f'A{recent_header_row}:G{recent_header_row}')
        ws[f'A{recent_header_row}'] = "Recent Disconnections (Last 30 Minutes Before Report Hour)"
        ws[f'A{recent_header_row}'].font = Font(name='Aptos', size=14, bold=True)
        ws[f'A{recent_header_row}'].alignment = Alignment(horizontal='left', vertical='center')
        ws.row_dimensions[recent_header_row].height = 25
        
        # Write recent disconnections data
        recent_start_row = recent_header_row + 1
        for r in dataframe_to_rows(recent_disconnections_df, index=False, header=True):
            ws.append(r)
        
        # Style the recent disconnections table
        recent_end_row = ws.max_row
        recent_header_font = Font(name='Aptos', size=11, bold=True)
        recent_normal_font = Font(name='Aptos', size=11)
        recent_header_fill = PatternFill(start_color='D3D3D3', end_color='D3D3D3', fill_type='solid')
        red_fill = PatternFill(start_color='FF6B6B', end_color='FF6B6B', fill_type='solid')
        
        for row in ws.iter_rows(min_row=recent_start_row, max_row=recent_end_row, min_col=1, max_col=7):
            for cell in row:
                cell.border = thin_border
                if cell.row == recent_start_row:
                    cell.font = recent_header_font
                    cell.fill = recent_header_fill
                    cell.alignment = Alignment(horizontal='center', vertical='center')
                else:
                    cell.font = recent_normal_font
                    # Alignments: Left for Machine Name, Center for others
                    if cell.column_letter in ['C']:
                        cell.alignment = Alignment(horizontal='left', vertical='center')
                    else:
                        cell.alignment = Alignment(horizontal='center', vertical='center')
        
        # Highlight still disconnected machines in red
        for idx, row in recent_disconnections_df.iterrows():
            # Check if Still Disconnected is True (handle string, numpy bool, etc.)
            still_disconnected = row.get('Still Disconnected', False)
            if str(still_disconnected).lower() == 'true' or still_disconnected == True:
                row_idx = recent_start_row + 1 + idx
                for col in range(1, 8):
                    cell = ws.cell(row=row_idx, column=col)
                    cell.fill = red_fill
        
        ws.row_dimensions[recent_start_row].height = 22

    # Add spacing before main disconnection table
    [ws.append([None]) for _ in range(2)]

    # Add section header for main disconnection table
    main_header_row = ws.max_row + 1
    ws.merge_cells(f'A{main_header_row}:F{main_header_row}')
    ws[f'A{main_header_row}'] = "Disconnections in a Day"
    ws[f'A{main_header_row}'].font = Font(name='Aptos', size=14, bold=True)
    ws[f'A{main_header_row}'].alignment = Alignment(horizontal='left', vertical='center')
    ws.row_dimensions[main_header_row].height = 25

    # Write Main Disconnection Table Headers & Data
    LOG.info("Writing main disconnection data to sheet")
    main_start_row = main_header_row + 1
    for r in dataframe_to_rows(df_disconn, index=False, header=True):
        ws.append(r)
    LOG.info(f"Main disconnection data written. Sheet max row: {ws.max_row}")

    # Style the main disconnection table
    start_row = main_start_row
    end_row = ws.max_row
    header_font = Font(name='Aptos', size=11, bold=True)
    normal_font = Font(name='Aptos', size=11)
    header_fill = PatternFill(start_color='D3D3D3', end_color='D3D3D3', fill_type='solid')

    for row in ws.iter_rows(min_row=start_row, max_row=end_row, min_col=1, max_col=6):
        for cell in row:
            cell.border = thin_border
            if cell.row == start_row:
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal='center', vertical='center')
            else:
                cell.font = normal_font
                # Alignments: Left for Machine Name, Center for others
                if cell.column_letter in ['C']:
                    cell.alignment = Alignment(horizontal='left', vertical='center')
                else:
                    cell.alignment = Alignment(horizontal='center', vertical='center')

    ws.row_dimensions[start_row].height = 22

    auto_adjust_column_widths(ws)

    add_header(ws, 'Toyota IIoT-Dashboard: Machine Disconnection Summary', 'A1:F1')
    add_timestamp(ws, 'A2:F2')



def add_header(ws, text, cell_range):
    ws.merge_cells(cell_range)
    cell = ws[cell_range.split(':')[0]]
    cell.value = text
    cell.font = Font(name='Aptos', size=16, bold=True)
    cell.alignment = Alignment(horizontal='left', vertical='center')
    apply_border(ws, cell_range)
    ws.row_dimensions[1].height = 30


def add_timestamp(ws, cell_range):
    ws.merge_cells(cell_range)
    cell = ws[cell_range.split(':')[0]]
    # Use IST timezone for consistent timestamp
    ist_now = datetime.now()
    cell.value = f'Generated On: {ist_now.strftime("%d.%m.%Y %H:%M:%S")} IST'
    cell.font = Font(name='Aptos', size=11, bold=True)
    cell.alignment = Alignment(horizontal='left', vertical='center')
    apply_border(ws, cell_range)
    ws.row_dimensions[2].height = 20


def add_section(ws, title, header_range, df, start_row):
    for r in dataframe_to_rows(df, index=False, header=True):
        ws.append(r)

    ws.merge_cells(header_range)
    ws[header_range.split(':')[0]] = title
    ws[header_range.split(':')[0]].font = Font(name='Aptos', size=14, bold=True)
    ws[header_range.split(':')[0]].alignment = Alignment(horizontal='left', vertical='center')

    ws.row_dimensions[int(header_range.split(':')[0][1:])].height = 25
    ws.row_dimensions[int(header_range.split(':')[0][1:]) + 1].height = 20
    # ws[header_range.split(':')[0]].fill = PatternFill(start_color='D3D3D3', end_color='D3D3D3', fill_type='solid')
    apply_border(ws, header_range)

    style_sheet_1(ws, start_row=start_row, start_col=1, end_row=ws.max_row, end_col=len(df.columns))
    apply_conditional_formatting(ws, start_row=start_row + 1, end_row=ws.max_row,
                                 days_col=6 if 'UNASSIGNED' in title else 6)


def style_sheet_0(ws, start_row, start_col, end_row, end_col, temp):
    header_font = Font(name='Aptos', size=11, bold=True)
    normal_font = Font(name='Aptos', size=11)
    header_fill = PatternFill(start_color='D3D3D3', end_color='D3D3D3', fill_type='solid')
    red_fill = PatternFill(start_color='ff7d7d', end_color='ff7d7d', fill_type='solid')
    white_fill = PatternFill(start_color='ffffff', end_color='ffffff', fill_type='solid')

    for row in ws.iter_rows(min_row=start_row, max_row=end_row, min_col=start_col, max_col=end_col):
        for cell in row:
            cell.border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'),
                                 bottom=Side(style='thin'))
            cell.alignment = Alignment(horizontal='center', vertical='center')

            if cell.row == start_row:
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal='center', vertical='center')
            else:
                cell.font = normal_font
                # cell.fill = PatternFill(start_color='F2F2F2' if cell.row % 2 == 0 else 'FFFFFF', end_color='F2F2F2'
                # if cell.row % 2 == 0 else 'FFFFFF', fill_type='solid')

    ws.cell(row=6, column=1).font = Font(name='Aptos', size=12, bold=True)
    ws.cell(row=6, column=1).alignment = Alignment(horizontal='center', vertical='center')
    ws.cell(row=8, column=1).font = Font(name='Aptos', size=12, bold=True)
    ws.cell(row=8, column=1).alignment = Alignment(horizontal='center', vertical='center')
    ws.cell(row=8, column=1).fill = white_fill if temp else red_fill


def style_sheet_1(ws, start_row, start_col, end_row, end_col):
    header_font = Font(name='Aptos', size=11, bold=True)
    normal_font = Font(name='Aptos', size=11)
    header_fill = PatternFill(start_color='D3D3D3', end_color='D3D3D3', fill_type='solid')

    for row in ws.iter_rows(min_row=start_row, max_row=end_row, min_col=start_col, max_col=end_col):
        for cell in row:
            cell.border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'),
                                 bottom=Side(style='thin'))
            cell.alignment = Alignment(horizontal='left' if cell.column_letter in ['B', 'C', 'D', 'E'] else 'center',
                                       vertical='center')

            if cell.row == start_row:
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal='center', vertical='center')
            else:
                cell.font = normal_font
                # cell.fill = PatternFill(start_color='F2F2F2' if cell.row % 2 == 0 else 'FFFFFF', end_color='F2F2F2'
                # if cell.row % 2 == 0 else 'FFFFFF', fill_type='solid')


def apply_conditional_formatting(ws, start_row, end_row, days_col):
    yellow_fill = PatternFill(start_color='ffd482', end_color='ffd482', fill_type='solid')
    red_fill = PatternFill(start_color='ff7d7d', end_color='ff7d7d', fill_type='solid')

    for row in ws.iter_rows(min_row=start_row, max_row=end_row):
        try:
            days = row[days_col - 1].value
            if days is not None:
                if int(days) > 40:
                    for cell in row:
                        cell.fill = red_fill
                elif int(days) > 10:
                    for cell in row:
                        cell.fill = yellow_fill
        except:
            pass


def auto_adjust_column_widths(ws):
    for column in ws.columns:
        if type(column[0]) != MergedCell:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(cell.value)
                except:
                    pass
            if column_letter == 'A':
                max_length = 5.5
            adjusted_width = (max_length + 2) * 1.15
            ws.column_dimensions[column_letter].width = adjusted_width


def apply_border(ws, cell_range):
    border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'),
                    bottom=Side(style='thin'))
    for row in ws[cell_range]:
        for cell in row:
            cell.border = border


def save_workbook(wb, filename):
    script_directory = os.path.dirname(os.path.abspath(__file__))
    full_path = os.path.join(script_directory, filename)

    # Ensure directory exists
    dir_path = os.path.dirname(full_path)
    if not os.path.exists(dir_path):
        LOG.info(f"Creating directory: {dir_path}")
        os.makedirs(dir_path, exist_ok=True)

    LOG.info(f"Saving workbook to: {full_path}")
    LOG.info(f"Directory exists: {os.path.exists(dir_path)}")
    LOG.info(f"Directory writable: {os.access(dir_path, os.W_OK)}")
    wb.save(full_path)
    LOG.info(f"Workbook saved successfully. File size: {os.path.getsize(full_path)} bytes")


# Usage Example:

# access_log_df: pandas DataFrame with columns:
#  ['Sl. No.', 'Timestamp', 'Company ID', 'Username', 'Fullname', 'Role']
# unassigned_df: pandas DataFrame with columns:
#  ['Sl. No.', 'Line', 'Machine', 'Parameter', 'Date of Identification', 'Days since Identification']
# assigned_df: pandas DataFrame with columns:
#  ['Sl. No.', 'Line', 'Machine', 'Parameter', 'Date of Identification', 'Days since Identification',
#  'Targeted Date of Completion', 'Responsible Person ID', 'Corrective Measurement', 'Spare Required', 'Support Needed']

access_log_df = pd.DataFrame({
    'Sl. No.': [0, 1, 2],
    'Timestamp': ['2024-03-13 08:10', '2024-03-13 09:15', '2024-03-13 10:20'],
    'Company ID': [600154, 600452, 600123],
    'Username': ['user1', 'user2', 'user3'],
    'Fullname': ['User One', 'User Two', 'User Three'],
    'Role': ['Admin', 'Operator', 'Guest']
})

access_log_df = pd.DataFrame({
    'Sl. No.': [0],
    'Timestamp': ['2024-03-13 08:10'],
    'Company ID': [600154],
    'Username': ['user1'],
    'Fullname': ['User One'],
    'Role': ['Admin']
})

unassigned_df = pd.DataFrame({
    'Sl. No.': [1, 2, 3, 4],
    'Line': ['HEAD', 'CRANK', 'HEAD', 'CRANK'],
    'Machine': ['H_OP180', 'C_OP250', 'H_OP180', 'C_OP250'],
    'Parameter': ['Parameter1', 'Parameter2', 'Parameter1', 'Parameter2'],
    'Date of Identification': ['2024-03-13', '2024-03-14', '2024-03-13', '2024-03-14'],
    'Days since Identification': [2, 7, 32, 36]
})

assigned_df = pd.DataFrame({
    'Sl. No.': [1, 2, 3, 4, 5, 6],
    'Line': ['BODY', 'HEAD', 'BODY', 'HEAD', 'BODY', 'HEAD'],
    'Machine': ['B_OP120', 'H_OP190', 'B_OP120', 'H_OP190', 'B_OP120', 'H_OP190'],
    'Parameter': ['Parameter3', 'Parameter4', 'Parameter3', 'Parameter4', 'Parameter3', 'Parameter4'],
    'Date of Identification': ['2024-03-15', '2024-03-16', '2024-03-15', '2024-03-16', '2024-03-15', '2024-03-16'],
    'Days since Identification': [3, 6, 32, 38, 50, 53],
    'Targeted Date of Completion': ['2024-03-20', '2024-03-21', '2024-03-20', '2024-03-21', '2024-03-20', '2024-03-21'],
    'Responsible Person ID': [600154, 600452, 600154, 600452, 600154, 600452],
    'Corrective Measurement': ['Measurement1', 'Measurement2', 'Measurement1', 'Measurement2', 'Measurement1',
                               'Measurement2'],
    'Spare Required': ['YES', 'NO', 'YES', 'NO', 'YES', 'NO'],
    'Support Needed': ['NO', 'YES', 'NO', 'YES', 'NO', 'YES']
})

if __name__ == '__main__':
    disconnection_df = pd.DataFrame({
        'Sl. No.': [1, 2],
        'Machine ID': [2, 3],
        'Machine Name': ['T_B_OP160', 'T_B_OP180'],
        'Disconnection Frequency': [2, 0],
        'Total Downtime (HH:MM:SS)': ['00:15:30', '00:00:00'],
        'Total Downtime (Minutes)': [15.5, 0.0]
    })
    create_excel_report(access_log_df, unassigned_df, assigned_df, disconnection_df, 'Toyota_IIoT_Dashboard_Log.xlsx')
    print('Log Created Successfully')
