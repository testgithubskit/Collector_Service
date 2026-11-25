import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ============================================================
# PostgreSQL Connection Parameters
# ============================================================
POSTGRES_HOST     = os.getenv("POSTGRES_HOST")
POSTGRES_PORT     = os.getenv("POSTGRES_PORT")
POSTGRES_DATABASE = os.getenv("POSTGRES_DATABASE")
POSTGRES_USER     = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")

DATABASE_URL = (
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DATABASE}"
)

# ============================================================
# Schema / Table names
# ============================================================
SCHEMA_NAME = "tiei_sample_4"
TABLE_NAME  = "sql_server_mct_data"


# ============================================================
# Helper: build a pyodbc connection string for SQL Server login
# Uses IP address + port + SQL username + password (no Windows auth)
# ============================================================
def _build_conn_string(prefix: str) -> str:
    """
    Build an ODBC connection string from env vars whose names
    start with `prefix` (e.g. 'SQL1_').

    Required env vars:
        {prefix}SERVER    → IP address or hostname of the SQL Server
        {prefix}PORT      → TCP port (default 1433)
        {prefix}DATABASE  → database name
        {prefix}USER      → SQL Server login username
        {prefix}PASSWORD  → SQL Server login password
        {prefix}DRIVER    → ODBC driver name (optional, default shown below)
    """
    server   = os.getenv(f"{prefix}SERVER",   "")
    port     = os.getenv(f"{prefix}PORT",     "1433")
    database = os.getenv(f"{prefix}DATABASE", "")
    driver   = os.getenv(f"{prefix}DRIVER",   "ODBC Driver 17 for SQL Server")
    user     = os.getenv(f"{prefix}USER",     "")
    password = os.getenv(f"{prefix}PASSWORD", "")

    return (
        f"DRIVER={{{driver}}};"
        f"SERVER={server},{port};"
        f"DATABASE={database};"
        f"UID={user};"
        f"PWD={password};"
        f"TrustServerCertificate=yes;"  # avoids SSL cert errors on internal servers
    )


# ============================================================
# SQL Servers configuration
#
# Each entry:
#   server_id         – unique label stored in sql_sync_state
#                       (per-server sync cursor)
#   connection_string – built from .env credentials
#   machine_mapping   – machine_number (str) → machine_id (int)
#                       for machines on THIS server only.
#                       Rows for unmapped machines are skipped.
#
# ⚠ Update machine_mapping dicts to match your physical layout.
# ============================================================
SQL_SERVERS = [
    {
        "server_id": "server_1",
        "connection_string": _build_conn_string("SQL1_"),
        "machine_mapping": {
            "Machine_1":  65,
            "Machine_2":  9,
            "Machine_3":  66,
            "Machine_5":  13,
            "Machine_6":  14,
            "Machine_7":  67,
            "Machine_8":  68,
            "Machine_9":  15,
            "Machine_10": 10,
            "Machine_11": 69,
            "Machine_12": 70,
            "Machine_13": 71,
            "Machine_14": 72,
            "Machine_15": 73,
            "Machine_16": 74,
            "Machine_17": 75,
            "Machine_18": 11,
            "Machine_19": 76,
            "Machine_20": 12,
            "Machine_21": 77,
            "Machine_22": 78,
            "Machine_23": 16,
            "Machine_24": 17,
            "Machine_25": 18,
            "Machine_26": 19,
            "Machine_27": 20,
            "Machine_28": 21,
            "Machine_29": 22,
            "Machine_30": 79,
            "Machine_31": 80,
            "Machine_32": 81,
            "Machine_33": 82,
            "Machine_34": 83,
            "Machine_35": 84

        },
    },
    {
        "server_id": "server_2",
        "connection_string": _build_conn_string("SQL2_"),
        "machine_mapping": {
            "Machine_1": 85,
            "Machine_2": 2,
            "Machine_3": 86,
            "Machine_4": 3,
            "Machine_5": 87,
            "Machine_6": 4,
            "Machine_7": 5,
            "Machine_8": 88,
            "Machine_9": 89,
            "Machine_10": 90,
            "Machine_11":6,
            "Machine_12":7,
            "Machine_13":8,
            "Machine_14":91,
            "Machine_15": 92,
            "Machine_17": 93,
            "Machine_18": 94,
            "Machine_19": 95,
            "Machine_20": 96,
            "Machine_21": 97,
            "Machine_22": 98,
            "Machine_23": 99,
            "Machine_24": 100,
            
        },
    },
    {
        "server_id": "server_3",
        "connection_string": _build_conn_string("SQL3_"),
        "machine_mapping": {
            "Machine_1":  23,
            "Machine_2":  40,
            "Machine_3":  101,
            "Machine_4":  49,
            "Machine_5":  55,
            "Machine_6":  57,
            "Machine_7":  59,
            "Machine_8":  24,
            "Machine_9":  26,
            "Machine_10": 28,
            "Machine_11": 30,
            "Machine_12": 32,
            "Machine_13": 34,
            "Machine_14": 36,
            "Machine_15": 38,
            "Machine_16": 58,
            "Machine_17": 60,
            "Machine_18": 25,
            "Machine_19": 27,
            "Machine_20": 29,
            "Machine_21": 31,
            "Machine_22": 33,
            "Machine_23": 35,
            "Machine_24": 37,
            "Machine_25": 39,
            "Machine_26": 102,
            "Machine_27": 103,
            "Machine_28": 104,
            "Machine_29": 41,
            "Machine_30": 42,
            "Machine_31": 43,
            "Machine_32": 44,
            "Machine_33": 45,
            "Machine_34": 46,
            "Machine_35": 47,
            "Machine_36": 105,
            "Machine_37": 48,
            "Machine_38": 106,
            "Machine_39": 107,
            "Machine_40": 50,
            "Machine_41": 51,
            "Machine_42": 52,
            "Machine_43": 53,
            "Machine_44": 54,
            "Machine_45": 56,
            "Machine_46": 108,
            "Machine_47": 109,
            "Machine_48": 110,
            "Machine_49": 111,
            "Machine_50": 112,
            "Machine_51": 113,
            "Machine_52": 114,
            "Machine_53": 115,
            "Machine_54": 116,
            "Machine_55": 117,
            "Machine_56": 118,
            "Machine_57": 119,
            "Machine_58": 120,
            "Machine_59": 121,
            "Machine_60": 122,
            
            
        },
    },
]


# ============================================================
# Cycle Time Parameter Mapping
# Maps machine_id to the parameter_id used for corrective activity tracking
# ============================================================
CYCLE_TIME_PARAMETER_MAPPING = {
    65: 7096,
    9: 7044,
    66: 7097,
    13: 7048,
    14: 7049,
    67: 7098,
    68: 7099,
    15: 7050,
    10: 7045,
    69: 7100,
    70: 7101,
    71: 7102,
    72: 7103,
    73: 7104,
    74: 7105,
    75: 7106,
    11: 7046,
    76: 7107,
    12: 7047,
    77: 7108,
    78: 7109,
    16: 7051,
    17: 7052,
    18: 7053,
    19: 7054,
    20: 7055,
    21: 7056,
    22: 7057,
    79: 7110,
    80: 7111,
    81: 7112,
    82: 7113,
    83: 7114,
    84: 7115,
    85: 7116,
    2: 7037,
    86: 7117,
    3: 7038,
    87: 7118,
    4: 7039,
    5: 7040,
    88: 7119,
    89: 7120,
    90: 7121,
    6: 7041,
    7: 7042,
    8: 7043,
    91: 7122,
    92: 7123,
    93: 7124,
    94: 7125,
    95: 7126,
    96: 7127,
    97: 7128,
    98: 7129,
    99: 7130,
    100: 7131,
    23: 7058,
    24: 7059,
    25: 7060,
    26: 7061,
    27: 7062,
    28: 7063,
    29: 7064,
    30: 7065,
    31: 7066,
    32: 7067,
    33: 7068,
    34: 7069,
    35: 7070,
    36: 7071,
    37: 7072,
    38: 7073,
    39: 7074,
    40: 7075,
    41: 7076,
    42: 7077,
    43: 7078,
    44: 7079,
    45: 7080,
    46: 7081,
    47: 7082,
    48: 7083,
    49: 7084,
    50: 7085,
    51: 7086,
    52: 7087,
    53: 7088,
    54: 7089,
    55: 7090,
    56: 7091,
    57: 7092,
    58: 7093,
    59: 7094,
    60: 7095,
    101: 7132,
    102: 7133,
    103: 7134,
    104: 7135,
    105: 7136,
    106: 7137,
    107: 7138,
    108: 7139,
    109: 7140,
    110: 7141,
    111: 7142,
    112: 7143,
    113: 7144,
    114: 7145,
    115: 7146,
    116: 7147,
    117: 7148,
    118: 7149,
    119: 7150,
    120: 7151,
    121: 7152,
    122: 7153,


}
