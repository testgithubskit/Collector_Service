import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def get_db_params(plant):
    if plant == 'localhost':
        return {
            'SCHEMA': os.getenv('LOCALHOST_SCHEMA'),
            'TIMESCALE_DB_PARAMS': {
                'provider': 'postgres',
                'host': os.getenv('LOCALHOST_DB_HOST'),
                'port': os.getenv('LOCALHOST_DB_PORT'),
                'user': os.getenv('LOCALHOST_DB_USER'),
                'password': os.getenv('LOCALHOST_DB_PASSWORD'),
                'database': os.getenv('LOCALHOST_DB_NAME')
            },
            'MONGO_DB_URL': os.getenv('LOCALHOST_MONGO_URL')
        }
    elif plant == 'tnga_plant':
        return {
            'SCHEMA': os.getenv('TNGA_SCHEMA'),
            'TIMESCALE_DB_PARAMS': {
                'provider': 'postgres',
                'host': os.getenv('TNGA_DB_HOST'),
                'port': os.getenv('TNGA_DB_PORT'),
                'user': os.getenv('TNGA_DB_USER'),
                'password': os.getenv('TNGA_DB_PASSWORD'),
                'database': os.getenv('TNGA_DB_NAME')
            },
            'MONGO_DB_URL': os.getenv('TNGA_MONGO_URL')
        }
    elif plant == 'gd_plant':
        return {
            'SCHEMA': os.getenv('GD_SCHEMA'),
            'TIMESCALE_DB_PARAMS': {
                'provider': 'postgres',
                'host': os.getenv('GD_DB_HOST'),
                'port': os.getenv('GD_DB_PORT'),
                'user': os.getenv('GD_DB_USER'),
                'password': os.getenv('GD_DB_PASSWORD'),
                'database': os.getenv('GD_DB_NAME')
            },
            'MONGO_DB_URL': os.getenv('GD_MONGO_URL')
        }
    else:
        raise ValueError(f"Unknown plant argument: {plant}")