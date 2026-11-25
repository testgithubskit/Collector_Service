from pony.orm import *
from datetime import datetime
db = Database()


class Machine(db.Entity):

    _table_ = ("tiei_sample_4", "machines")

    id = PrimaryKey(int, auto=True)

    name = Required(str)

    location = Required(str)

    machine_number = Optional(str)

    short_name = Optional(str)

    description = Optional(str)

    enabled = Optional(bool)

    parameters = Optional(int)


class CycleTimeLimits(db.Entity):

    _table_ = ("tiei_sample_4", "cycle_time_limits")

    id = PrimaryKey(int, auto=True)

    machine_id = Required(int)

    warning_limit = Required(float)

    critical_limit = Required(float)

    status = Optional(str)


class PressureMonitoringMachine(db.Entity):

    _table_ = ("tiei_sample_4", "pressure_monitoring_machine")

    id = PrimaryKey(int, auto=True)

    machine_name = Required(str)

    warning_limit = Required(float)

    critical_limit = Required(float)

    status = Optional(str)


class CorrectiveActivity(db.Entity):

    _table_ = ("tiei_sample_4", "corrective_activity")

    id = PrimaryKey(int, auto=True)

    machine_parameters_id = Required(int)

    date_of_identification = Required(datetime)

    latest_occurrence = Required(datetime)

    target_date_of_completion = Optional(datetime)

    number_of_occurrences = Required(int)

    corrective_measurement = Optional(str)

    spare_required = Optional(str)

    support_needed = Optional(str)

    priority = Optional(str)

    responsible_person_id = Optional(int)

    recent_value = Optional(float)

    parameter_condition_id = Required(int)


# ==========================================================
# PRESSURE LOG FILE
# ==========================================================

class PressureLogFile(db.Entity):

    _table_ = ("tiei_sample_4", "pressure_log_file")

    id = PrimaryKey(int, auto=True)

    machine_id = Required(int)

    file_name = Required(str)


    processed_time = Optional(
        datetime,
        default=lambda: datetime.now()
    )
    baseline = Optional(bool, default=False)
    time_stamp = Optional(datetime)
    mean_pressure = Optional(float)
    peak_pressure = Optional(float)
    start_time = Optional(datetime)
    end_time = Optional(datetime)
    cycle_duration_seconds = Optional(float)
    pressure_ripple = Optional(float)
    rmse = Optional(float)
    status = Optional(str)
    latest_time = Optional(datetime)