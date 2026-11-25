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

SCHEMA_NAME = "tiei_gd_plant_1"

TABLE_NAME = "sql_server_mct_data"


machine_map_1 = {
    "B_OP10": 1,
    "B_OP20": 2,
    "B_OP30": 3,
    "B_OP40": 4,
    "B_OP50": 5,
    "B_OP60": 6,
    "B_OP70": 7,
    "B_OP80": 8,
    "B_OP90": 9,
    "B_OP110": 10,
    "B_OP120": 11,
    "B_OP130": 12,
    "B_OP140": 13,
    "B_OP150": 14,
    "B_OP160": 15,
    "B_OP180": 16,
    "B_OP190": 17,
    "B_OP200": 18,
    "B_OP210": 19,
    "B_OP220": 20,
    "B_OP230": 21,
    "B_OP240": 22,
    "B_OP250": 23,
    "B_OP260": 24,
    "B_OP270": 25,
    "B_OP280": 26,
    "B_OP300": 27,
    "B_OP310": 28,
    "B_OP320": 29,
    "B_OP330": 30,
    "B_OP340": 31,
    "B_OP350": 32,
    "B_OP360": 33,
    "B_OP370": 34,
    "B_OP380": 35,
    "B_OP400": 36,
    "B_OP470": 37,
    "B_OP480": 38,

    "C_OP10": 39,
    "C_OP40": 40,
    "C_OP50A": 41,
    "C_OP50B": 42,
    "C_OP50C": 43,
    "C_OP80A": 44,
    "C_OP80B": 45,
    "C_OP80C": 46,
    "C_OP90": 47,
    "C_OP150": 48,
    "C_OP180": 49,

    "H_OP10": 50,
    "H_OP20": 51,
    "H_OP30": 52,
    "H_OP40": 53,
    "H_OP50": 54,
    "H_OP55": 55,
    "H_OP60": 56,
    "H_OP70": 57,
    "H_OP80": 58,
    "H_OP90": 59,
    "H_OP100": 60,
    "H_OP110": 61,
    "H_OP120": 62,
    "H_OP130": 63,
    "H_OP140": 64,
    "H_OP150": 65,
    "H_OP160": 66,
    "H_OP170": 67,
    "H_OP180": 68,
    "H_OP190": 69,
    "H_OP210": 70,
    "H_OP220": 71,
    "H_OP230": 72,
    "H_OP240": 73,
    "H_OP250": 74,
    "H_OP260": 75,
    "H_OP270": 76,
    "H_OP280": 77,
    "H_OP420": 78,
    "H_OP430": 79,
    "H_OP440": 80,
    "H_OP450": 81,
    "H_OP460": 82,
    "H_OP470": 83,
    "H_OP480": 84,
    "H_OP490": 85,
    "H_OP500": 86
    
}
