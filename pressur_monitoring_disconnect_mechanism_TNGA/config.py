import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# PostgreSQL Connection Parameters from .env file
POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_PORT = os.getenv("POSTGRES_PORT")
POSTGRES_DATABASE = os.getenv("POSTGRES_DATABASE")
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")

# Construct DATABASE_URL from individual parameters
DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DATABASE}"

MONGODB_URL = os.getenv("MONGODB_URL")

SCHEMA_NAME = "tiei_sample_4"

machine_map = {
    "T_B_OP160": 2,
    "T_B_OP180": 3,
    "T_B_OP195A": 4,
    "T_B_OP195B": 5,
    "T_B_OP230": 6,
    "T_B_OP235": 7,
    "T_B_OP540": 8,
    "T_C_OP10": 9,   #machine_2
    "T_C_OP100": 10, #machine_10
    "T_C_OP160": 11, #machine_18
    "T_C_OP190": 12, #machine_20
    "T_C_OP30": 13,  #machine_5
    "T_C_OP40": 14,  #machine_6
    "T_C_OP90": 15,  #machine_9
    "T_C_OP910": 16, #machine_23
    "T_C_OP911": 17, #machine_24
    "T_C_OP912": 18, #machine_25
    "T_C_OP913": 19, #machine_26
    "T_C_OP914": 20, #machine_27
    "T_C_OP915": 21, #machine_28
    "T_C_OP916": 22, #machine_29
    "T_H_OP10": 23,
    "T_H_OP100A": 24,
    "T_H_OP100B": 25,
    "T_H_OP110A": 26,
    "T_H_OP110B": 27,
    "T_H_OP120A": 28,
    "T_H_OP120B": 29,
    "T_H_OP140A": 30,
    "T_H_OP140B": 31,
    "T_H_OP150A": 32,
    "T_H_OP150B": 33,
    "T_H_OP160A": 34,
    "T_H_OP160B": 35,
    "T_H_OP170A": 36,
    "T_H_OP170B": 37,
    "T_H_OP180A": 38,
    "T_H_OP180B": 39,
    "T_H_OP20": 40,
    "T_H_OP230": 41,
    "T_H_OP240": 42,
    "T_H_OP250": 43,
    "T_H_OP260": 44,
    "T_H_OP270": 45,
    "T_H_OP280": 46,
    "T_H_OP285": 47,
    "T_H_OP300": 48,
    "T_H_OP50": 49,
    "T_H_OP500": 50,
    "T_H_OP510": 51,
    "T_H_OP520": 52,
    "T_H_OP530": 53,
    "T_H_OP540": 54,
    "T_H_OP55": 55,
    "T_H_OP550": 56,
    "T_H_OP80A": 57,
    "T_H_OP80B": 58,
    "T_H_OP90A": 59,
    "T_H_OP90B": 60
}



SQL_SERVER_CONNECTION_STRING = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=localhost\\SQLEXPRESS;"
    "DATABASE=Machine_DB;"
    "Trusted_Connection=yes;"
)

TABLE_NAME = "sql_server_mct_data"

# SQL Server machine mapping
MACHINE_MAPPING = {
    "Machine_1": 1,
    "Machine_2": 2,
    "Machine_3": 3,
    "Machine_5": 5,
    "Machine_6": 6,
    "Machine_7": 7,
    "Machine_8": 8,
    "Machine_9": 9,
    "Machine_10": 10,
    "Machine_11": 11,
    "Machine_12": 12,
    "Machine_13": 13,
    "Machine_14": 14,
    "Machine_15": 15,
    "Machine_16": 16,
    "Machine_17": 17,
    "Machine_18": 18,
    "Machine_19": 19,
    "Machine_20": 20,
    "Machine_21": 21
}
