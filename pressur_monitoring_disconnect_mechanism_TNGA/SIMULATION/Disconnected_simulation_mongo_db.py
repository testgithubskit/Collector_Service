from pymongo import MongoClient
import time

import os
from dotenv import load_dotenv

# Load .env from parent directory
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# MongoDB Connection
MONGODB_URL = os.getenv("MONGODB_URL")
mongo_client = MongoClient(MONGODB_URL)
mongo_db = mongo_client["MtLinki"]
collection = mongo_db["L1Signal_Pool_Active"]

try:

    current_value = True

    while True:

        result = collection.update_one(
            {
                "L1Name": "T_B_OP160",
                "signalname": "DISCONNECT"
            },
            {
                "$set": {
                    "value": current_value
                }
            }
        )

        print(
            f"T_B_OP160 DISCONNECT value updated to "
            f"{current_value}"
        )

        current_value = not current_value

        time.sleep(5)

except KeyboardInterrupt:

    print("Stopped.")

finally:

    mongo_client.close()