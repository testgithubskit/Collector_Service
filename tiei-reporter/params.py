
import os
# DB_PARAMS = {
#     'provider': 'postgres',
#     'host': '10.82.126.73',
#     'user': 'tnga_iot_3',
#     'password': 'Toyota_2022',
#     'database': 'tiei_test'
# }

# SCHEMA_1 = 'tiei_sample_4'
# SCHEMA_2 = 'tiei_gd_plant_1'

# fromaddr = "lohith.s@tiei.toyota-industries.com"
# toaddr = ["lohith.s@tiei.toyota-industries.com"]

SCHEMA_1 = os.getenv('SCHEMA_1', 'tiei_sample_4')
SCHEMA_2 = os.getenv('SCHEMA_2', 'tiei_gd_plant_1')


# DB_PARAMS = {
#     'provider': 'postgres',
#     'host': '172.18.100.87',
#     'port': '5432',
#     'user': 'postgres',
#     'password': '1234',
#     'database': 'Toyota_Demo'
# }
DB_PARAMS = {
    'provider': os.getenv('DB_PROVIDER', 'postgres'),
    'host': os.getenv('DB_HOST', '10.82.126.43'),
    'port': os.getenv('DB_PORT', '5435'),
    'user': os.getenv('DB_USER', 'tnga_iot'),
    'password': os.getenv('DB_PASSWORD', 'Toyota_2026'),
    'database': os.getenv('DB_NAME', 'tiei_test')
}


# fromaddr = "gokulravi925@gmail.com"
# toaddr = ["gokulravi925@gmail.com"]

fromaddr = os.getenv('FROM_ADDR', "pedigitalization@tiei.toyota-industries.com")
toaddr = [os.getenv('TO_ADDR', "lohith.s@tiei.toyota-industries.com")]