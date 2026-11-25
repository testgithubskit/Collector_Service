from datetime import datetime, time, timedelta, timezone
import time as tt
import os
REPORT_HOUR = int(os.getenv('REPORT_HOUR', '17'))

# IST timezone (UTC+5:30)
IST_OFFSET = timedelta(hours=5, minutes=30)
TZ_IST = timezone(IST_OFFSET)


from pony.orm import Database

from email_sender import send_email
from helpers import get_user_access_logs, get_corrective_activity_logs, get_machine_disconnections, get_recent_disconnections
from logs.logger_module import LOG
from pony_entity_model import pony_entities
from params import *
from report_generator import create_excel_report

EMAIL_SENT_LOG_FILE = 'email_sent_log.txt'


def read_last_email_sent_timestamp():
    """Read the last email sent timestamp from the log file."""
    if os.path.exists(EMAIL_SENT_LOG_FILE):
        try:
            with open(EMAIL_SENT_LOG_FILE, 'r') as f:
                timestamp_str = f.read().strip()
                if timestamp_str:
                    return datetime.fromisoformat(timestamp_str)
        except Exception as e:
            LOG.error(f"Error reading email sent log: {e}")
    return datetime.now() - timedelta(days=1)


def write_email_sent_timestamp(timestamp):
    """Write the email sent timestamp to the log file."""
    try:
        with open(EMAIL_SENT_LOG_FILE, 'w') as f:
            f.write(timestamp.isoformat())
    except Exception as e:
        LOG.error(f"Error writing email sent log: {e}")


if __name__ == '__main__':

    try:
        LOG.info('=' * 50)
        LOG.info('SCRIPT INITIALIZED!')
        LOG.info(f'REPORT_HOUR set to: {REPORT_HOUR}:00')
        LOG.info('=' * 50)

        db_tnga = Database()
        db_gd = Database()

        pony_entities(db_tnga, schema=SCHEMA_1)
        pony_entities(db_gd, schema=SCHEMA_2)

        db_tnga.bind(**DB_PARAMS)
        db_gd.bind(**DB_PARAMS)

        db_tnga.generate_mapping(create_tables=False)
        db_gd.generate_mapping(create_tables=False)

        LOG.info('ORM Mapped Successfully to the Database!')

        recorded_timestamp = read_last_email_sent_timestamp()
        print(f'Recorded timestamp: {recorded_timestamp}')


        while True:
            try:
                current_timestamp = datetime.now().replace(tzinfo=TZ_IST)
                LOG.info(f'Current time: {current_timestamp.strftime("%Y-%m-%d %H:%M:%S")}, Report hour: {REPORT_HOUR}:00')
                LOG.info(f'Last email sent date: {recorded_timestamp.date()}, Current date: {current_timestamp.date()}')
                LOG.info(f'Can send email: {current_timestamp.date() != recorded_timestamp.date() and current_timestamp.time() >= time(REPORT_HOUR, 0)}')

                if current_timestamp.date() != recorded_timestamp.date() and current_timestamp.time() >= time(REPORT_HOUR, 0):
                    # TNGA Plant Report Generation
                    LOG.info("Starting TNGA Plant Report Generation")
                    tnga_ual, tnga_len_ual = get_user_access_logs(current_timestamp.date(), db_tnga)
                    LOG.info(f"TNGA user access logs fetched: {tnga_len_ual} records")

                    tnga_una_df, tnga_len_una_df, tnga_a_df, tnga_len_a_df = get_corrective_activity_logs(db_tnga)
                    LOG.info(f"TNGA corrective activity logs fetched: {tnga_len_una_df} unassigned, {tnga_len_a_df} assigned")
                    
                    # Calculate Warning and Critical counts from unassigned abnormalities based on parameter_condition_id
                    # parameter_condition_id: Warning, Critical (mapped from 2, 3)
                    tnga_warning_count = len(tnga_una_df[tnga_una_df['parameter_condition_id'] == 'Warning']) if 'parameter_condition_id' in tnga_una_df.columns else 0
                    tnga_critical_count = len(tnga_una_df[tnga_una_df['parameter_condition_id'] == 'Critical']) if 'parameter_condition_id' in tnga_una_df.columns else 0

                    tnga_file_name = f'TNGA_Toyota_IIoT_Dashboard_Log {current_timestamp.date()}.xlsx'
                    tnga_disconn_df = get_machine_disconnections(current_timestamp.date(), SCHEMA_1)
                    LOG.info(f"TNGA machine disconnections fetched: {len(tnga_disconn_df)} records")
                    
                    # Fetch recent disconnections (last 30 min before report hour)
                    tnga_recent_disconn_df = get_recent_disconnections(current_timestamp.date(), SCHEMA_1, REPORT_HOUR)
                    LOG.info(f"TNGA recent disconnections fetched: {len(tnga_recent_disconn_df)} records")
                    
                    # Count still disconnected machines (from recent disconnections)
                    tnga_disconnected_machines = len(tnga_recent_disconn_df[tnga_recent_disconn_df['Still Disconnected'] == True]) if not tnga_recent_disconn_df.empty else 0

                    create_excel_report(tnga_ual, tnga_una_df, tnga_a_df, tnga_disconn_df, tnga_recent_disconn_df, f'reports/TNGA/{tnga_file_name}')

                    LOG.info(f'TNGA Report Generated Successfully >> {tnga_file_name}')

                    # GD Plant Report Generation
                    LOG.info("Starting GD Plant Report Generation")
                    gd_ual, gd_len_ual = get_user_access_logs(current_timestamp.date(), db_gd)
                    LOG.info(f"GD user access logs fetched: {gd_len_ual} records")

                    gd_una_df, gd_len_una_df, gd_a_df, gd_len_a_df = get_corrective_activity_logs(db_gd)
                    LOG.info(f"GD corrective activity logs fetched: {gd_len_una_df} unassigned, {gd_len_a_df} assigned")
                    
                    # Calculate Warning and Critical counts from unassigned abnormalities based on parameter_condition_id
                    # parameter_condition_id: Warning, Critical (mapped from 2, 3)
                    gd_warning_count = len(gd_una_df[gd_una_df['parameter_condition_id'] == 'Warning']) if 'parameter_condition_id' in gd_una_df.columns else 0
                    gd_critical_count = len(gd_una_df[gd_una_df['parameter_condition_id'] == 'Critical']) if 'parameter_condition_id' in gd_una_df.columns else 0

                    gd_file_name = f'GD_Toyota_IIoT_Dashboard_Log {current_timestamp.date()}.xlsx'
                    gd_disconn_df = get_machine_disconnections(current_timestamp.date(), SCHEMA_2)
                    LOG.info(f"GD machine disconnections fetched: {len(gd_disconn_df)} records")
                    
                    # Fetch recent disconnections (last 30 min before report hour)
                    gd_recent_disconn_df = get_recent_disconnections(current_timestamp.date(), SCHEMA_2, REPORT_HOUR)
                    LOG.info(f"GD recent disconnections fetched: {len(gd_recent_disconn_df)} records")
                    
                    # Count still disconnected machines (from recent disconnections)
                    gd_disconnected_machines = len(gd_recent_disconn_df[gd_recent_disconn_df['Still Disconnected'] == True]) if not gd_recent_disconn_df.empty else 0

                    create_excel_report(gd_ual, gd_una_df, gd_a_df, gd_disconn_df, gd_recent_disconn_df, f'reports/GD/{gd_file_name}')

                    LOG.info(f'GD Report Generated Successfully >> {gd_file_name}')

                    LOG.info("Starting email sending process")
                    try:
                        send_email(tnga_file_name, gd_file_name, tnga_len_ual, tnga_len_una_df, tnga_len_a_df, tnga_warning_count, tnga_critical_count, tnga_disconnected_machines, gd_len_ual, gd_len_una_df, gd_len_a_df, gd_warning_count, gd_critical_count, gd_disconnected_machines, db_tnga)
                        LOG.info(f'Report Mail Successfully Sent')

                        recorded_timestamp = current_timestamp
                        write_email_sent_timestamp(recorded_timestamp)
                        print(f'Recorded timestamp: {recorded_timestamp}')
                    except Exception as email_error:
                        LOG.error(f"Error sending email: {email_error}")
                        LOG.error("Email sending failed - report was generated but not sent")
                        LOG.error("Timestamp will NOT be updated - will retry on next cycle")

                else:
                    tt.sleep(60)
            except Exception as e:
                LOG.error(e)
                break
                tt.sleep(60)

    except Exception as e:
        LOG.error(e)
    finally:
        try:
            db_tnga.disconnect()
            db_gd.disconnect()
            LOG.info('Database Connections Closed')
        except Exception as e:
            LOG.error(f"Error closing database connections: {e}")
