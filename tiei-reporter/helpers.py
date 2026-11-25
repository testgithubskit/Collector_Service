from datetime import datetime, timedelta, timezone
from logs.logger_module import LOG
import pandas as pd
from pony.orm import db_session, select, desc

# Timezone offset
IST_OFFSET = timedelta(hours=5, minutes=30)
TZ_IST = timezone(IST_OFFSET)


@db_session
def get_user_access_logs(timestamp_date, db):
    try:
        user_history = select(
            (i.timestamp, i.user_id.company_id, i.user_id.username, i.user_id.full_name, i.user_id.role)
            for i in db.UserAccessLog if (i.timestamp + IST_OFFSET).date() == timestamp_date)[:]

        last_user = select(
            (i.timestamp, i.user_id.company_id, i.user_id.username, i.user_id.full_name, i.user_id.role)
            for i in db.UserAccessLog
            if (i.timestamp + IST_OFFSET).date() < timestamp_date
        ).order_by(lambda: desc(i.timestamp)).first()

        df = pd.DataFrame([last_user] + user_history,
                          columns=['Timestamp', 'Company ID', 'Username', 'Fullname', 'Role'])
        df.insert(0, 'Sl. No.', range(1, len(df) + 1))

        df['Timestamp'] = df['Timestamp'].apply(
            lambda x: (x + IST_OFFSET).replace(tzinfo=None) if pd.notnull(x) else None)
        return df, len(user_history)

    except Exception as e:
        LOG.error(e)
        return pd.DataFrame(), 0


@db_session
def get_corrective_activity_logs(db):
    try:
        logs = select((i.machine_parameter.machine.name,
                       i.machine_parameter.machine.location,
                       i.machine_parameter.name,
                       i.date_of_identification,
                       i.latest_occurrence,
                       i.target_date_of_completion,
                       i.number_of_occurrences,
                       i.corrective_measurement,
                       i.spare_required,
                       i.support_needed,
                       i.priority,
                       i.parameter_condition.id,
                       i.responsible_person.id)
                      for i in db.CorrectiveActivity).order_by(lambda: desc(i.date_of_identification))[:]

        df = pd.DataFrame(logs,
                          columns=['Machine', 'Location', 'Parameter', 'Date of Identification', 'Latest Occurrence',
                                   'Target Date of Completion', 'Number of Occurrences', 'Corrective Measurement',
                                   'Spare Required', 'Support Needed', 'Priority', 'parameter_condition_id', 'Responsible Person ID'])

        # Map parameter_condition_id to readable text
        condition_map = {2: 'Warning', 3: 'Critical'}
        df['parameter_condition_id'] = df['parameter_condition_id'].map(condition_map).fillna(df['parameter_condition_id'])

        # Remove timezone from datetime columns
        if 'Latest Occurrence' in df.columns:
            df['Latest Occurrence'] = pd.to_datetime(df['Latest Occurrence']).apply(
                lambda x: x.replace(tzinfo=None) if pd.notnull(x) else None)

        # Use Location column directly from machines table
        df['Line'] = df['Location']

        df['Date of Identification'] = pd.to_datetime(df['Date of Identification']).apply(
            lambda x: (x + IST_OFFSET).replace(tzinfo=None) if pd.notnull(x) else None)

        current_date = datetime.now().date()
        df['DIC'] = pd.to_datetime(df['Date of Identification']).dt.date
        df['Days since Identification'] = (pd.to_datetime(current_date) - pd.to_datetime(df['DIC'])).dt.days
        df = df.drop(columns=['DIC'])

        assigned = df[df['Responsible Person ID'].notnull()]
        unassigned = df[df['Responsible Person ID'].isnull()]

        unassigned = unassigned[
            ['Line', 'Machine', 'Parameter', 'Date of Identification', 'Days since Identification', 'parameter_condition_id']]
        unassigned.insert(0, 'Sl. No.', range(1, len(unassigned) + 1))

        assigned = assigned[['Line', 'Machine', 'Parameter', 'Date of Identification', 'Days since Identification',
                             'Responsible Person ID', 'Target Date of Completion', 'Corrective Measurement',
                             'Spare Required', 'Support Needed']]

        # Remove timezone from datetime columns in assigned DataFrame
        if 'Target Date of Completion' in assigned.columns:
            assigned['Target Date of Completion'] = pd.to_datetime(assigned['Target Date of Completion']).apply(
                lambda x: x.replace(tzinfo=None) if pd.notnull(x) else None)

        assigned.insert(0, 'Sl. No.', range(1, len(assigned) + 1))

        return unassigned, len(unassigned), assigned, len(assigned)

    except Exception as e:
        LOG.error(e)
        return pd.DataFrame(), 0, pd.DataFrame(), 0


import psycopg2
from params import DB_PARAMS
from datetime import time, timezone

def get_machine_disconnections(report_date, schema):
    """
    Retrieves the machine disconnection list and calculates frequencies and total downtime
    for the specified report_date.
    """
    try:
        # Establish connection using psycopg2
        conn = psycopg2.connect(
            host=DB_PARAMS['host'],
            port=DB_PARAMS.get('port', '5432'),
            user=DB_PARAMS['user'],
            password=DB_PARAMS['password'],
            database=DB_PARAMS['database']
        )
        cur = conn.cursor()

        # DB stores IST wall-clock times with +00 offset; use UTC frame to match stored values
        day_start = datetime.combine(report_date, time.min).replace(tzinfo=timezone.utc)
        
        current_time = datetime.now().replace(tzinfo=timezone.utc)
        if report_date == current_time.date():
            day_end = current_time
        else:
            day_end = datetime.combine(report_date, time.max).replace(tzinfo=timezone.utc)

        # Retrieve machine details and overlapping disconnections
        query = f"""
            SELECT m.id, m.name, dh.start_time, dh.stop_time
            FROM "{schema}"."machines" m
            LEFT JOIN "{schema}"."disconnection_history1" dh ON m.id = dh.machine_id
            AND dh.start_time <= %s AND (dh.stop_time >= %s OR dh.stop_time IS NULL)
            ORDER BY m.id
        """
        cur.execute(query, (day_end, day_start))
        rows = cur.fetchall()
        cur.close()
        conn.close()

        # Process data in python
        machine_stats = {}
        for mach_id, name, start_time, stop_time in rows:
            if mach_id not in machine_stats:
                machine_stats[mach_id] = {
                    'Machine ID': mach_id,
                    'Machine Name': name,
                    'Disconnection Frequency': 0,
                    'Total Downtime Seconds': 0.0
                }

            if start_time is not None:
                # Calculate overlap
                effective_start = max(start_time, day_start)
                effective_stop = min(stop_time if stop_time is not None else day_end, day_end)
                
                if effective_stop > effective_start:
                    downtime_seconds = (effective_stop - effective_start).total_seconds()
                    machine_stats[mach_id]['Disconnection Frequency'] += 1
                    machine_stats[mach_id]['Total Downtime Seconds'] += downtime_seconds

        # Build DataFrame
        df_list = []
        for mach_id, stats in machine_stats.items():
            seconds = stats['Total Downtime Seconds']
            hours = int(seconds // 3600)
            mins = int((seconds % 3600) // 60)
            secs = int(seconds % 60)
            hhmmss = f"{hours:02d}:{mins:02d}:{secs:02d}"
            
            df_list.append({
                'Machine ID': stats['Machine ID'],
                'Machine Name': stats['Machine Name'],
                'Disconnection Frequency': stats['Disconnection Frequency'],
                'Total Downtime (HH:MM:SS)': hhmmss,
                'Total Downtime (Minutes)': round(seconds / 60.0, 2)
            })

        df = pd.DataFrame(df_list)
        if not df.empty:
            # Filter out machines with 0 disconnection frequency
            df = df[df['Disconnection Frequency'] > 0]
            # Sort by total downtime descending, then machine id ascending
            df = df.sort_values(by=['Total Downtime (Minutes)', 'Machine ID'], ascending=[False, True]).reset_index(drop=True)
            df.insert(0, 'Sl. No.', range(1, len(df) + 1))
        else:
            df = pd.DataFrame(columns=['Sl. No.', 'Machine ID', 'Machine Name', 'Disconnection Frequency', 'Total Downtime (HH:MM:SS)', 'Total Downtime (Minutes)'])
        
        return df

    except Exception as e:
        LOG.error(f"Error in get_machine_disconnections: {e}")
        return pd.DataFrame(columns=['Sl. No.', 'Machine ID', 'Machine Name', 'Disconnection Frequency', 'Total Downtime (HH:MM:SS)', 'Total Downtime (Minutes)'])


def get_recent_disconnections(report_date, schema, report_hour):
    """
    Retrieves machines that disconnected in the last 30 minutes before the report hour.
    Returns DataFrame with machine info, frequency, downtime, and still_disconnected flag.
    """
    try:
        # Establish connection using psycopg2
        conn = psycopg2.connect(
            host=DB_PARAMS['host'],
            port=DB_PARAMS.get('port', '5432'),
            user=DB_PARAMS['user'],
            password=DB_PARAMS['password'],
            database=DB_PARAMS['database']
        )
        cur = conn.cursor()

        # Define time boundaries: 30 minutes before report hour to report hour
        # DB stores IST wall-clock times with +00 offset; use UTC frame to match
        report_time = datetime.combine(report_date, time(report_hour, 0)).replace(tzinfo=timezone.utc)
        window_start = report_time - timedelta(minutes=30)
        window_end = report_time

        # Retrieve machine details and disconnections in the 30-minute window
        query = f"""
            SELECT m.id, m.name, dh.start_time, dh.stop_time
            FROM "{schema}"."machines" m
            LEFT JOIN "{schema}"."disconnection_history1" dh ON m.id = dh.machine_id
            AND dh.start_time <= %s AND (dh.stop_time >= %s OR dh.stop_time IS NULL)
            ORDER BY m.id
        """
        cur.execute(query, (window_end, window_start))
        rows = cur.fetchall()
        cur.close()
        conn.close()

        # Process data in python
        machine_stats = {}
        for mach_id, name, start_time, stop_time in rows:
            if mach_id not in machine_stats:
                machine_stats[mach_id] = {
                    'Machine ID': mach_id,
                    'Machine Name': name,
                    'Disconnection Frequency': 0,
                    'Total Downtime Seconds': 0.0,
                    'Still Disconnected': False
                }

            if start_time is not None:
                # Calculate overlap with the 30-minute window
                effective_start = max(start_time, window_start)
                effective_stop = min(stop_time if stop_time is not None else window_end, window_end)
                
                if effective_stop > effective_start:
                    downtime_seconds = (effective_stop - effective_start).total_seconds()
                    machine_stats[mach_id]['Disconnection Frequency'] += 1
                    machine_stats[mach_id]['Total Downtime Seconds'] += downtime_seconds
                    
                    # Check if still disconnected at report hour
                    if stop_time is None or stop_time >= window_end:
                        machine_stats[mach_id]['Still Disconnected'] = True

        # Build DataFrame
        df_list = []
        for mach_id, stats in machine_stats.items():
            if stats['Disconnection Frequency'] > 0:  # Only include machines with disconnections
                seconds = stats['Total Downtime Seconds']
                hours = int(seconds // 3600)
                mins = int((seconds % 3600) // 60)
                secs = int(seconds % 60)
                hhmmss = f"{hours:02d}:{mins:02d}:{secs:02d}"
                
                df_list.append({
                    'Machine ID': stats['Machine ID'],
                    'Machine Name': stats['Machine Name'],
                    'Disconnection Frequency': stats['Disconnection Frequency'],
                    'Total Downtime (HH:MM:SS)': hhmmss,
                    'Total Downtime (Minutes)': round(seconds / 60.0, 2),
                    'Still Disconnected': stats['Still Disconnected']
                })

        df = pd.DataFrame(df_list)
        if not df.empty:
            # Sort by still disconnected first, then by downtime descending
            df = df.sort_values(by=['Still Disconnected', 'Total Downtime (Minutes)'], ascending=[False, False]).reset_index(drop=True)
            df.insert(0, 'Sl. No.', range(1, len(df) + 1))
        else:
            df = pd.DataFrame(columns=['Sl. No.', 'Machine ID', 'Machine Name', 'Disconnection Frequency', 'Total Downtime (HH:MM:SS)', 'Total Downtime (Minutes)', 'Still Disconnected'])
        
        return df

    except Exception as e:
        LOG.error(f"Error in get_recent_disconnections: {e}")
        return pd.DataFrame(columns=['Sl. No.', 'Machine ID', 'Machine Name', 'Disconnection Frequency', 'Total Downtime (HH:MM:SS)', 'Total Downtime (Minutes)', 'Still Disconnected'])

