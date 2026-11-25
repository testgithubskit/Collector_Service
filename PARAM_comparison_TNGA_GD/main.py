import time
import argparse
from datetime import datetime
from pony.orm import Database, db_session, select, commit
from pymongo import MongoClient
from logger_module import setup_logger
from mongodb_queries import *
from pony_entity_model import pony_entities
from params import *

if __name__ == '__main__':
    print("Script starting...")
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Run the script with a specific plant configuration.')
    parser.add_argument('plant', choices=['localhost', 'tnga_plant', 'gd_plant'],
                        help='Choose between localhost, tnga_plant, or gd_plant')

    args = parser.parse_args()
    print(f"Plant argument: {args.plant}")

    client = None
    db = None

    try:
        LOG = setup_logger(args.plant)
        LOG.info('\n\n' + '#' * 50 + '\nSCRIPT INITIALIZED!\n')

        # Get database parameters based on the provided argument
        config = get_db_params(args.plant)
        SCHEMA = config['SCHEMA']
        TIMESCALE_DB_PARAMS = config['TIMESCALE_DB_PARAMS']
        MONGO_DB_URL = config['MONGO_DB_URL']

        # Initialize Pony ORM and MongoDB
        print("Initializing database connections...")
        db = Database()
        print("Database object created")
        pony_entities(db, schema=SCHEMA)
        print("Entities defined")
        db.bind(**TIMESCALE_DB_PARAMS)
        print("Database bound")
        try:
            db.generate_mapping(create_tables=False)
            print("ORM Mapped Successfully to the Database!")
        except Exception as e:
            print(f"ERROR during generate_mapping: {e}")
            raise
        LOG.info('ORM Mapped Successfully to the Database!')

        client = MongoClient(MONGO_DB_URL)
        print("MongoDB client created")
        db_mongo = client['MTLINKi']['L1Signal_Pool_Active']
        print("MongoDB Connected Successfully!")
        LOG.info('MongoDB Connected Successfully!')

        try:
            while True:
                try:
                    LOG.info(f'\n--- Starting new iteration at {datetime.now()} ---')
                    print(f'--- Starting new iteration at {datetime.now()} ---')
                    with db_session:
                        comparisons = select(pc for pc in db.ParameterComparison)[:]
                        LOG.info(f'Processing {len(comparisons)} parameter comparisons')
                        print(f'Processing {len(comparisons)} parameter comparisons')

                        for i in comparisons:
                            LOG.info(f'\nProcessing comparison ID: {i.id}, Line: {i.line}')
                            print(f'Processing comparison ID: {i.id}, Line: {i.line}')
                            param_1 = next(db_mongo.aggregate(search_parameter(i.machine_parameter1.name)), None)
                            param_2 = next(db_mongo.aggregate(search_parameter(i.machine_parameter2.name)), None)

                            if param_1:
                                i.time_1 = param_1['updatedate']
                                if param_1['value'] is not None:
                                    i.value_1 = param_1['value']
                                LOG.info(f'  Param1 ({i.machine_parameter1.name}): value={i.value_1}, time={i.time_1}')
                                print(f'  Param1 ({i.machine_parameter1.name}): value={i.value_1}, time={i.time_1}')
                            else:
                                LOG.warning(f'  Param1 ({i.machine_parameter1.name}) not found in MongoDB')
                                print(f'  Param1 ({i.machine_parameter1.name}) not found in MongoDB')

                            if param_2:
                                i.time_2 = param_2['updatedate']
                                if param_2['value'] is not None:
                                    i.value_2 = param_2['value']
                                LOG.info(f'  Param2 ({i.machine_parameter2.name}): value={i.value_2}, time={i.time_2}')
                                print(f'  Param2 ({i.machine_parameter2.name}): value={i.value_2}, time={i.time_2}')
                            else:
                                LOG.warning(f'  Param2 ({i.machine_parameter2.name}) not found in MongoDB')
                                print(f'  Param2 ({i.machine_parameter2.name}) not found in MongoDB')

                            if i.value_1 and i.value_2:
                                i.difference = int(((i.value_2 - i.value_1) / i.value_1) * 100)
                                LOG.info(f'  Difference: {i.difference}%')
                                print(f'  Difference: {i.difference}%')

                                if abs(i.difference) > i.critical_limit:
                                    i.parameter_condition = db.ParameterCondition[3]
                                    LOG.warning(f'  Condition: CRITICAL (>{i.critical_limit}%)')
                                    print(f'  Condition: CRITICAL (>{i.critical_limit}%)')
                                elif abs(i.difference) > i.warning_limit:
                                    i.parameter_condition = db.ParameterCondition[2]
                                    LOG.warning(f'  Condition: WARNING (>{i.warning_limit}%)')
                                    print(f'  Condition: WARNING (>{i.warning_limit}%)')
                                else:
                                    i.parameter_condition = db.ParameterCondition[1]
                                    LOG.info(f'  Condition: NORMAL')
                                    print(f'  Condition: NORMAL')

                                # Corrective Activity Logic for Warning and Critical conditions
                                if i.parameter_condition and i.parameter_condition.id in [2, 3] and i.param_comparison_id:
                                    current_time = datetime.now()
                                    current_value = i.value_2

                                    # Check if combination (param_comparison_id, parameter_condition_id) already exists
                                    existing_activity = select(
                                        ca for ca in db.CorrectiveActivity
                                        if ca.machine_parameter.id == i.param_comparison_id.id
                                        and ca.parameter_condition.id == i.parameter_condition.id
                                    ).first()

                                    if existing_activity:
                                        # Update existing record
                                        existing_activity.latest_occurrence = current_time
                                        existing_activity.recent_value = current_value
                                        existing_activity.number_of_occurrences += 1
                                        LOG.info(f'  Corrective Activity UPDATED: Occurrence #{existing_activity.number_of_occurrences}')
                                        print(f'  Corrective Activity UPDATED: Occurrence #{existing_activity.number_of_occurrences}')
                                    else:
                                        # Insert new record using psycopg2 directly to avoid Pony ORM cache issues
                                        try:
                                            import psycopg2
                                            conn = psycopg2.connect(
                                                host=TIMESCALE_DB_PARAMS['host'],
                                                port=TIMESCALE_DB_PARAMS['port'],
                                                user=TIMESCALE_DB_PARAMS['user'],
                                                password=TIMESCALE_DB_PARAMS['password'],
                                                database=TIMESCALE_DB_PARAMS['database']
                                            )
                                            cur = conn.cursor()
                                            cur.execute('''
                                                INSERT INTO {}.corrective_activity
                                                (machine_parameters_id, date_of_identification, parameter_condition_id, recent_value, latest_occurrence, number_of_occurrences)
                                                VALUES (%s, %s, %s, %s, %s, %s)
                                            '''.format(SCHEMA),
                                                (i.param_comparison_id.id, current_time, i.parameter_condition.id,
                                                 current_value, current_time, 1))
                                            conn.commit()
                                            cur.close()
                                            conn.close()
                                            LOG.info(f'  Corrective Activity INSERTED: New record created')
                                            print(f'  Corrective Activity INSERTED: New record created')
                                        except Exception as e:
                                            print(f'  Error creating CorrectiveActivity: {e}')
                                            # Fallback: try to find and update existing
                                            existing = select(
                                                ca for ca in db.CorrectiveActivity
                                                if ca.machine_parameter.id == i.param_comparison_id.id
                                                and ca.parameter_condition.id == i.parameter_condition.id
                                            ).first()
                                            if existing:
                                                existing.latest_occurrence = current_time
                                                existing.recent_value = current_value
                                                existing.number_of_occurrences += 1
                                                print(f'  Fallback: Updated existing activity instead')
                                elif i.parameter_condition and i.parameter_condition.id in [2, 3]:
                                    LOG.info(f'  Skipping Corrective Activity: param_comparison_id is NULL')
                                    print(f'  Skipping Corrective Activity: param_comparison_id is NULL')
                            else:
                                LOG.info(f'  Skipping comparison: One or both values missing')
                                print(f'  Skipping comparison: One or both values missing')

                            commit()

                    LOG.info('Iteration completed. Sleeping for 5 seconds...')
                    print('Iteration completed. Sleeping for 5 seconds...')
                    time.sleep(5)
                except Exception as e:
                    print(f"ERROR in main loop: {e}")
                    import traceback
                    traceback.print_exc()
                    raise
        except KeyboardInterrupt:
            LOG.info('Process interrupted by user')

    except Exception as e:
        LOG.error(e)

    finally:
        if db:
            db.disconnect()
        if client:
            client.close()
        LOG.info('Database Connection Closed')
