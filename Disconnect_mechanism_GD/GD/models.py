from pony.orm import *
from datetime import datetime
db = Database()


class Machine(db.Entity):

    _table_ = ("tiei_gd_plant_1", "machines")

    id = PrimaryKey(int, auto=True)

    name = Required(str)

    location = Required(str)

    machine_number = Optional(str)

    short_name = Optional(str)

    description = Optional(str)

    enabled = Optional(bool)

    parameters = Optional(int)


class CycleTimeLimits(db.Entity):

    _table_ = ("tiei_gd_plant_1", "cycle_time_limits")

    id = PrimaryKey(int, auto=True)

    machine_id = Required(int)

    warning_limit = Required(float)

    critical_limit = Required(float)

    status = Optional(str)



# ==========================================================
# PRESSURE LOG FILE
# ==========================================================
