"""
ORM Read Operation Module
==========================

The `read_operation` module within the `orm` subpackage provides functions to read records from the database
using Object-Relational Mapping (ORM) tools. It includes functionalities to retrieve existing records from the
database tables represented by ORM entities.

Functions
---------
- `read_user_records`: Function to retrieve user records from the database.
- `read_product_records`: Function to retrieve product records from the database.
- `read_order_records`: Function to retrieve order records from the database.
- ... (add more functions as needed)

"""

# Standard library imports
import logging

# Related third-party imports
from pony.orm import db_session, commit, select, raw_sql

# Local module imports
import collector_app.database.orm.pony_entity_model as pony_models

LOGGER = logging.getLogger(__name__)


@db_session(optimistic=False)
def select_activities_by_machine_params(ids):
    """Selects CorrectiveActivity instances with machine_parameter IDs matching those in the provided list.

    Args:
        ids: A list of machine parameter IDs to match.

    Returns:
        A list of tuples, where each tuple contains the ID and machine_parameter ID of a matching CorrectiveActivity instance.
    """

    results = select(ca.machine_parameter.id for ca in pony_models.CorrectiveActivity if
                     ca.machine_parameter.id in ids)
    return results[:]


@db_session(optimistic=False)
def select_activities_by_machine_params_condition(unique_combinations):
    """Selects CorrectiveActivity instances with machine_parameter IDs and condition
     matching those in the provided list.

    Args:
        unique_combinations: A list of tuple of machine parameter IDs and condition to match.

    Returns:
        A list of tuples, where each tuple contains the ID and machine_parameter ID of a
         matching CorrectiveActivity instance.
    """

    unique_combinations_tuple = tuple(unique_combinations)

    if len(unique_combinations_tuple) == 1:
        # Handle the case when there is only one combination
        unique_combinations_tuple_str = str(unique_combinations_tuple)[:-2] + ')'
    else:
        # Handle the case when there is only one combination
        unique_combinations_tuple_str = str(unique_combinations_tuple)

    query_result = select(
        ca.machine_parameter.id for ca in pony_models.CorrectiveActivity if
        raw_sql('(machine_parameters_id,'
                ' parameter_condition_id)'
                f' IN {unique_combinations_tuple_str}'))

    for result in list(query_result):
        print(result)
    return list(query_result)


@db_session(optimistic=False)
def get_corrective_activities_by_params(param_ids):
    """Retrieves corrective activity objects with machine_parameter IDs matching those in the provided list.

    Args:
        param_ids: A list of machine parameter IDs to match.

    Returns:
        A list of CorrectiveActivity objects that match the criteria.
    """

    results = select((ca.id, ca.machine_parameter.id, ca.latest_occurrence, ca.recent_value,
                      ca.number_of_occurrences, ca.warning_occurrences,
                      ca.critical_occurrences) for ca in pony_models.CorrectiveActivity if
                     ca.machine_parameter.id in param_ids)
    return list(results)  # Materialize the results as a list


@db_session(optimistic=False)
def get_ignored_parameter_ids():
    """Retrieves all machine parameter ids that are ignored currently for criticality.

    Returns:
        A list of machine parameter ids.
    """

    query = select(ip.machine_parameter.id for ip in pony_models.IgnoredParameter)
    machine_parameter_ids = list(query)

    return machine_parameter_ids


@db_session(optimistic=False)
def get_axis_name(parameter_name):
    """Retrieves the axis(that is the display name) for the given parameter name.

    Args:
        parameter_name: The parameter name whose display name is required.

    Returns:
        The display name for the parameter.
    """

    results = select(mp.display_name for mp in pony_models.MachineParameter if
                     mp.name == parameter_name)

    return list(results)[0]  # Materialize the results as a list


@db_session
def query_all_machine_parameters():
    # Define the query to retrieve machine parameters and related information
    query_result = select(
        (mp.name, mp.warning_limit, mp.critical_limit, mp.display_name, mp.parameter_group.group_name)
        for mp in pony_models.MachineParameter
    )

    # Execute the query and fetch the results
    results = query_result[:]

    data_warning = {parameter[0]: parameter[1] for parameter in results}
    data_critical = {parameter[0]: parameter[2] for parameter in results}
    display_name = {parameter[0]: parameter[3] for parameter in results}
    group_name = {parameter[0]: parameter[4] for parameter in results}

    return data_warning, data_critical, display_name, group_name
