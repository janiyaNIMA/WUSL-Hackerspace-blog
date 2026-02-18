import os
import json
from pymongo import MongoClient
from dotenv import load_dotenv
from bson.objectid import ObjectId

load_dotenv()
client = MongoClient(os.getenv('MONGO_URI'))
users_col = client['hackerspace_auth']['users']

def check_admin():
    admin = users_col.find_one({"email": "admin@wusl.com"})
    if admin:
        print(f"ADMIN DATA: {json.dumps({k: str(v) for k, v in admin.items()}, indent=2)}")
    else:
        print("ADMIN NOT FOUND in MongoDB")

if __name__ == "__main__":
    check_admin()
