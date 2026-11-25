import os
from dotenv import load_dotenv
from dataclasses import dataclass
from typing import Optional, Dict

load_dotenv()


@dataclass
class InfluxDBConfig:
    """Configuration for a single InfluxDB instance"""
    host: str
    port: int
    username: str
    password: str
    database: str
    ssl: bool = True
    verify_ssl: bool = False

    @classmethod
    def from_env(cls, prefix: str) -> 'InfluxDBConfig':
        """Create config from environment variables with given prefix"""
        return cls(
            host=os.getenv(f"{prefix}_HOST"),
            port=int(os.getenv(f"{prefix}_PORT", "8086")),
            username=os.getenv(f"{prefix}_USERNAME"),
            password=os.getenv(f"{prefix}_PASSWORD"),
            database=os.getenv(f"{prefix}_DATABASE"),
            ssl=os.getenv(f"{prefix}_SSL", "true").lower() == "true",
            verify_ssl=os.getenv(f"{prefix}_VERIFY_SSL", "false").lower() == "true"
        )


@dataclass
class PostgreSQLConfig:
    """Configuration for PostgreSQL database"""
    host: str
    port: int
    database: str
    username: str
    password: str
    schema: str = "public"

    @classmethod
    def from_env(cls) -> 'PostgreSQLConfig':
        """Create config from environment variables"""
        return cls(
            host=os.getenv("POSTGRES_HOST"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            database=os.getenv("POSTGRES_DATABASE"),
            username=os.getenv("POSTGRES_USERNAME"),
            password=os.getenv("POSTGRES_PASSWORD"),
            schema=os.getenv("POSTGRES_SCHEMA", "tiei_sample_4")
        )


# InfluxDB Instance 1 Configuration
INFLUXDB_1 = InfluxDBConfig.from_env("INFLUXDB_1")

# InfluxDB Instance 2 Configuration
INFLUXDB_2 = InfluxDBConfig.from_env("INFLUXDB_2")

# InfluxDB Instance 3 Configuration
INFLUXDB_3 = InfluxDBConfig.from_env("INFLUXDB_3")

# InfluxDB Instance 4 Configuration
INFLUXDB_4 = InfluxDBConfig.from_env("INFLUXDB_4")

# PostgreSQL Configuration
POSTGRES = PostgreSQLConfig.from_env()

# Machine to InfluxDB instance mapping
# Maps machine names to their corresponding InfluxDB instance (1, 2, 3, or 4)
MACHINE_INFLUX_MAPPING: Dict[str, int] = {
    "T_C_OP200": 1,  # T_C_OP200 uses INFLUXDB_1
    "T_H_OP280": 2,  # T_H_OP280 uses INFLUXDB_2
    "T_B_OP220": 3,  # T_B_OP220 uses INFLUXDB_3
    "T_H_OP285": 4,  # T_H_OP285 uses INFLUXDB_4
}

# Machine to SQL Server MCT machine_id mapping
# Maps machine names to their machine_id in sql_server_mct_data table
MACHINE_SQL_MCT_ID_MAPPING: Dict[str, int] = {
    "T_C_OP200": 77,  # T_C_OP200 -> machine_id 77
    "T_H_OP280": 46,  # T_H_OP280 -> machine_id 46
    "T_B_OP220": 90,  # T_B_OP220 -> machine_id 90
    "T_H_OP285": 47,  # T_H_OP285 -> machine_id 47
}

# Machine configuration with port mappings
# This will be stored in PostgreSQL vibration_machines table
# port1/port2 are human-readable names for database storage
# InfluxDB measurement names are mapped separately
MACHINE_CONFIG = {
    "T_C_OP200": {
        "machine_name": "T_C_OP200",
        "machine_location": "CRANK",
        "port1": "MOTOR",
        "port2": "BLOWER"
    },
    "T_H_OP280": {
        "machine_name": "T_H_OP280",
        "machine_location": "HEAD",
        "port1": "MOTOR",
        "port2": "JET PUMP"
    },
    "T_B_OP220": {
        "machine_name": "T_B_OP220",
        "machine_location": "BODY",
        "port1": "MOTOR",
        "port2": "BLOWER"
    },
    "T_H_OP285": {
        "machine_name": "T_H_OP285",
        "machine_location": "HEAD",
        "port1": "MOTOR",
        "port2": "BLOWER"
    }
}

# Mapping from human-readable port names to actual InfluxDB measurement names
PORT_INFLUX_MAPPING = {
    "MOTOR": "port1",
    "BLOWER": "port2",
    "JET PUMP": "port2"
}

# Parameter mapping for abnormality detection
# Maps (machine_name, port, parameter_name) -> (corrective_activity_param_id, vibration_parameters_table_id)
# corrective_activity_param_id: Used for corrective_activity table
# vibration_parameters_table_id: Used to fetch warning/critical limits from vibration_parameters table
PARAMETER_MAPPING = {
    "T_C_OP200": {
        "MOTOR": {
            "contact_temperature": {"corrective_id": 7022, "vibration_table_id": 1},
            "v_peak_x": {"corrective_id": 7021, "vibration_table_id": 2},
            "v_peak_y": {"corrective_id": 7020, "vibration_table_id": 3},
            "v_peak_z": {"corrective_id": 7019, "vibration_table_id": 4},
            "v_rms_x": {"corrective_id": 7018, "vibration_table_id": 5},
            "v_rms_y": {"corrective_id": 7017, "vibration_table_id": 6},
            "v_rms_z": {"corrective_id": 7016, "vibration_table_id": 7}
        },
        "BLOWER": {
            "contact_temperature": {"corrective_id": 7015, "vibration_table_id": 8},
            "v_peak_x": {"corrective_id": 7014, "vibration_table_id": 9},
            "v_peak_y": {"corrective_id": 7013, "vibration_table_id": 10},
            "v_peak_z": {"corrective_id": 7012, "vibration_table_id": 11},
            "v_rms_x": {"corrective_id": 7011, "vibration_table_id": 12},
            "v_rms_y": {"corrective_id": 7010, "vibration_table_id": 13},
            "v_rms_z": {"corrective_id": 7009, "vibration_table_id": 14}
        }
    },
    "T_H_OP280": {
        "MOTOR": {
            "contact_temperature": {"corrective_id": 7036, "vibration_table_id": 15},
            "v_peak_x": {"corrective_id": 7035, "vibration_table_id": 16},
            "v_peak_y": {"corrective_id": 7034, "vibration_table_id": 17},
            "v_peak_z": {"corrective_id": 7033, "vibration_table_id": 18},
            "v_rms_x": {"corrective_id": 7032, "vibration_table_id": 19},
            "v_rms_y": {"corrective_id": 7031, "vibration_table_id": 20},
            "v_rms_z": {"corrective_id": 7030, "vibration_table_id": 21}
        },
        "JET PUMP": {
            "contact_temperature": {"corrective_id": 7029, "vibration_table_id": 22},
            "v_peak_x": {"corrective_id": 7028, "vibration_table_id": 23},
            "v_peak_y": {"corrective_id": 7027, "vibration_table_id": 24},
            "v_peak_z": {"corrective_id": 7026, "vibration_table_id": 25},
            "v_rms_x": {"corrective_id": 7025, "vibration_table_id": 26},
            "v_rms_y": {"corrective_id": 7024, "vibration_table_id": 27},
            "v_rms_z": {"corrective_id": 7023, "vibration_table_id": 28}
        }
    },
    "T_B_OP220": {
        "MOTOR": {
            "contact_temperature": {"corrective_id": 7181, "vibration_table_id": 29},
            "v_peak_x": {"corrective_id": 7180, "vibration_table_id": 30},
            "v_peak_y": {"corrective_id": 7179, "vibration_table_id": 31},
            "v_peak_z": {"corrective_id": 7178, "vibration_table_id": 32},
            "v_rms_x": {"corrective_id": 7177, "vibration_table_id": 33},
            "v_rms_y": {"corrective_id": 7176, "vibration_table_id": 34},
            "v_rms_z": {"corrective_id": 7175, "vibration_table_id": 35}
        },
        "BLOWER": {
            "contact_temperature": {"corrective_id": 7174, "vibration_table_id": 36},
            "v_peak_x": {"corrective_id": 7173, "vibration_table_id": 37},
            "v_peak_y": {"corrective_id": 7172, "vibration_table_id": 38},
            "v_peak_z": {"corrective_id": 7171, "vibration_table_id": 39},
            "v_rms_x": {"corrective_id": 7170, "vibration_table_id": 40},
            "v_rms_y": {"corrective_id": 7169, "vibration_table_id": 41},
            "v_rms_z": {"corrective_id": 7168, "vibration_table_id": 42}
        }
    },
    "T_H_OP285": {
        "MOTOR": {
            "contact_temperature": {"corrective_id": 7167, "vibration_table_id": 43},
            "v_peak_x": {"corrective_id": 7166, "vibration_table_id": 44},
            "v_peak_y": {"corrective_id": 7165, "vibration_table_id": 45},
            "v_peak_z": {"corrective_id": 7164, "vibration_table_id": 46},
            "v_rms_x": {"corrective_id": 7163, "vibration_table_id": 47},
            "v_rms_y": {"corrective_id": 7162, "vibration_table_id": 48},
            "v_rms_z": {"corrective_id": 7161, "vibration_table_id": 49}
        },
        "BLOWER": {
            "contact_temperature": {"corrective_id": 7160, "vibration_table_id": 50},
            "v_peak_x": {"corrective_id": 7159, "vibration_table_id": 51},
            "v_peak_y": {"corrective_id": 7158, "vibration_table_id": 52},
            "v_peak_z": {"corrective_id": 7157, "vibration_table_id": 53},
            "v_rms_x": {"corrective_id": 7156, "vibration_table_id": 54},
            "v_rms_y": {"corrective_id": 7155, "vibration_table_id": 55},
            "v_rms_z": {"corrective_id": 7154, "vibration_table_id": 56}
        }
    }
}
